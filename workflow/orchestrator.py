"""Workflow orchestrator for managing multi-agent workflows."""

import asyncio
import os
from typing import Dict, Any
from agents.intent_agent import IntentAgent
from agents.analyse_handoff_agent import AnalyseHandoffAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.predict_requirement_agent import PredictRequirementAgent
from agents.classify_step_agent import ClassifyStepAgent
from agents.profile_agent import ProfileAgent
from agents.up_sales_cross_sales_agent import UpSalesCrossSalesAgent
from agents.sales_agent import SalesAgent
from agents.guardrail_agent import GuardrailAgent
from agents.models import IntentAgentInput, AnalyseHandoffInput, OrchestratorAgentInput
from agents.models import (
    PredictRequirementInput,
    ClassifyStepInput,
    SalesGraph,
    ProfileAgentInput,
    HistoricalData,
    UpSalesCrossSalesInput,
    Requirements,
    ProductCombo,
    SalesAgentInput,
    GuardrailInput,
)
from workflow.debug import print_agent_results
from workflow.memory_manager import MemoryManager
from database.postgres.session_service import update_session_handoff, get_or_create_session
from database.catalog_adapter import list_products_for_shop

from config import DEMO_SHOP_ID, DEMO_SHOP_NAME, USE_DB_CATALOG


class WorkflowOrchestrator:
    """Orchestrates workflows across multiple agents."""

    def __init__(self):
        """Initialize the orchestrator with all agents."""
        self.intent_agent = IntentAgent()
        self.analyse_handoff_agent = AnalyseHandoffAgent()
        self.orchestrator_agent = OrchestratorAgent()
        # Sales pipeline agents (Phase 2/3)
        self.predict_requirement_agent = PredictRequirementAgent()
        self.classify_step_agent = ClassifyStepAgent()
        self.profile_agent = ProfileAgent()
        self.up_sales_cross_sales_agent = UpSalesCrossSalesAgent()
        self.sales_agent = SalesAgent()
        self.guardrail_agent = GuardrailAgent()
        self._memory_managers: Dict[str, MemoryManager] = {}

    async def process_user_message(
        self,
        user_id: str,
        session_id: str,
        raw_message: str,
        language: str = "vi",
    ) -> Dict[str, Any]:
        """Process a user message through intent, handoff analysis, and orchestration.

        Args:
            user_id: User identifier
            session_id: Session identifier
            raw_message: Raw user message
            language: Language code (default: "vi")

        Returns:
            Dictionary containing intent, handoff analysis, and orchestrated task
        """
        phase_trace: list[str] = []

        def _normalize_text(s: str) -> str:
            return (s or "").strip().lower()

        def _heuristic_pick_combo(
            raw_message: str,
            explicit: list[str],
            implicit: list[str],
            combos: list[ProductCombo],
        ) -> ProductCombo | None:
            """Best-effort deterministic combo selection.

            This is used as a fallback when the LLM-based UpSalesCrossSalesAgent
            doesn't reliably pick a combo (common for direct price questions).
            """
            haystack = " ".join(
                [_normalize_text(raw_message)]
                + [_normalize_text(x) for x in (explicit or [])]
                + [_normalize_text(x) for x in (implicit or [])]
            )
            if not haystack.strip():
                return None

            # Prefer combos whose name appears in the message/requirements.
            for c in combos:
                for p in c.products:
                    token = _normalize_text(p).replace("_", " ")
                    if token and token in haystack:
                        return c

            # Common Vietnamese keyword heuristics.
            keyword_map = {
                "hoodie": ["hoodie", "áo hoodie", "ao hoodie"],
                "ao thun": ["áo thun", "ao thun", "t-shirt", "tee"],
                "ao so mi": ["áo sơ mi", "ao so mi", "sơ mi", "so mi"],
            }
            for c in combos:
                combo_name = " ".join([_normalize_text(c.combo_id)] + [_normalize_text(p) for p in c.products])
                for _k, kws in keyword_map.items():
                    if any(kw in haystack for kw in kws) and any(kw in combo_name for kw in kws):
                        return c

            return None

        # Get or create memory manager for this session
        if session_id not in self._memory_managers:
            self._memory_managers[session_id] = MemoryManager(session_id=session_id)

        memory_manager = self._memory_managers[session_id]

        # Phase 0: reception
        phase_trace.append("Phase 0: receive_input (user)")
        await memory_manager.receive_input(
            role="user",
            content=raw_message,
            tokens=0,  # Will be calculated if needed
            intent=None,  # Will be set after intent agent
        )

        # Prepare input data
        intent_input = IntentAgentInput(
            user_id=user_id,
            session_id=session_id,
            raw_message=raw_message,
            language=language,
        )

        handoff_input = AnalyseHandoffInput(
            user_id=user_id,
            session_id=session_id,
            raw_message=raw_message,
            language=language,
        )

        # Phase 1: Initial analysis (parallel)
        phase_trace.append("Phase 1: IntentAgent + AnalyseHandoffAgent (parallel)")
        intent_result, handoff_result = await asyncio.gather(
            self.intent_agent.run(intent_input),
            self.analyse_handoff_agent.run(handoff_input),
        )

        # Prepare orchestrator input from both results
        orchestrator_input = OrchestratorAgentInput(
            user_id=user_id,
            clean_intent_text=intent_result.clean_intent_text,
            intent_code=intent_result.intent_code,
            policy_flags=handoff_result.policy_flags,
            emotion_score=handoff_result.emotion_score,
            handoff_required=handoff_result.handoff_required,
            handoff_reason=handoff_result.handoff_reason,
            risk_level=handoff_result.risk_level,
        )

        phase_trace.append("Phase 1: OrchestratorAgent (task selection)")
        orchestrator_result = await self.orchestrator_agent.run(orchestrator_input)

        # Update active context with intent and handoff info
        memory_manager.update_active_context(
            extracted_entities={"intent_code": intent_result.intent_code},
        )

        final_response_text: str
        phase_trace.append(f"Phase 1 result: task={orchestrator_result.task}")

        # Phase 2/3: Sales pipeline
        # Note: We *continue* the conversation even when task == human_handle.
        # "human_handle" here means "escalate/flag for human", not "stop responding".
        # This prevents the chat from feeling like it resets every turn.
        phase_trace.append("Phase 2: Sales workflow")
        if orchestrator_result.task in {"sales_task", "human_handle"}:

            # Short-term memory for downstream agents
            phase_trace.append("Phase 2.0: Load short memory")
            short_memory = memory_manager.get_conversation_history(max_messages=20)
            # Convert ConversationMessage objects to simple dicts (agents expect list-like)
            short_memory_dicts = []
            for m in short_memory:
                if hasattr(m, "role") and hasattr(m, "content"):
                    short_memory_dicts.append({"role": m.role, "content": m.content})
                else:
                    short_memory_dicts.append(m)

            # 2.1 Predict requirements
            phase_trace.append("Phase 2.1: PredictRequirementAgent")
            predict_input = PredictRequirementInput(
                latest_message=raw_message,
                short_memory=short_memory_dicts,
                sales_node="greeting",
            )
            requirement_result = await self.predict_requirement_agent.run(predict_input)

            # 2.2 Classify sales step
            phase_trace.append("Phase 2.2: ClassifyStepAgent")
            default_nodes = [
                "greeting",
                "need_discovery",
                "solution_matching",
                "price_discussion",
                "objection_handling",
                "closing",
            ]
            classify_input = ClassifyStepInput(
                clean_intent_text=intent_result.clean_intent_text,
                sales_graph=SalesGraph(nodes=default_nodes, current_node="greeting"),
            )
            step_result = await self.classify_step_agent.run(classify_input)

            # 2.3 Profile customer (no real historical data wired yet; safe defaults)
            phase_trace.append("Phase 2.3: ProfileAgent")
            profile_input = ProfileAgentInput(
                user_id=user_id,
                historical_data=HistoricalData(total_orders=0, total_spend=0.0, last_purchase_days=0),
                label_definitions=["VIP", "tiềm năng", "bình thường", "chí tôn"],
            )
            profile_result = await self.profile_agent.run(profile_input)

            # 2.4 Upsell/cross-sell (no inventory wired yet; use demo combos)
            phase_trace.append("Phase 2.4: UpSalesCrossSalesAgent")

            use_db_catalog = USE_DB_CATALOG

            available_combos: list[ProductCombo]
            if use_db_catalog:
                phase_trace.append("Phase 2.4a: Load products from DB catalog")
                # Demo default: use a single fixed shop unless explicitly overridden.
                shop_id = os.getenv("SHOP_ID", str(DEMO_SHOP_ID))
                phase_trace.append(f"Demo shop: {DEMO_SHOP_NAME} ({shop_id})")
                products = list_products_for_shop(shop_id)
                # Map products -> simple 1-product "combo" for now.
                available_combos = [
                    ProductCombo(
                        combo_id=(p.sku or p.id),
                        products=[p.name],
                        stock=int(p.stock_quantity),
                        price=float(p.price),
                    )
                    for p in products
                ]
                if not available_combos:
                    phase_trace.append("Phase 2.4a: DB empty -> fallback to demo combos")
                    available_combos = [
                        ProductCombo(combo_id="DEMO-01", products=["ao_thun_basic"], stock=10),
                        ProductCombo(combo_id="DEMO-02", products=["ao_so_mi"], stock=5),
                    ]
            else:
                available_combos = [
                    ProductCombo(combo_id="DEMO-01", products=["ao_thun_basic"], stock=10, price=199000.0),
                    ProductCombo(combo_id="DEMO-02", products=["ao_so_mi"], stock=5, price=349000.0),
                    ProductCombo(combo_id="DEMO-03", products=["ao_hoodie"], stock=12, price=499000.0),
                ]

            upsell_input = UpSalesCrossSalesInput(
                requirements=Requirements(
                    explicit=requirement_result.explicit_requirements,
                    implicit=requirement_result.implicit_requirements,
                ),
                available_combos=available_combos,
                short_memory=short_memory_dicts,
                summary_conversation=None,
            )
            upsell_result = await self.up_sales_cross_sales_agent.run(upsell_input)

            # Find the selected combo details
            selected_product_combo = None
            if upsell_result.selected_combo:
                selected_product_combo = next(
                    (c for c in available_combos if c.combo_id == upsell_result.selected_combo),
                    None
                )

            # Deterministic fallback: for direct price/availability questions, try a heuristic match.
            if selected_product_combo is None:
                maybe_price_intent = any(
                    kw in _normalize_text(raw_message)
                    for kw in ["giá", "bao nhiêu", "price", "cost", "tiền"]
                )
                if maybe_price_intent:
                    phase_trace.append("Phase 2.4b: Fallback combo selection (heuristic)")
                    selected_product_combo = _heuristic_pick_combo(
                        raw_message,
                        requirement_result.explicit_requirements,
                        requirement_result.implicit_requirements,
                        available_combos,
                    )
                    if selected_product_combo:
                        phase_trace.append(
                            f"Phase 2.4b: Selected {selected_product_combo.combo_id} (price={selected_product_combo.price})"
                        )

            # 2.5 Sales response generation
            phase_trace.append("Phase 2.5: SalesAgent")
            sales_input = SalesAgentInput(
                customer_label=profile_result.customer_label,
                sales_node=step_result.current_sales_node,
                requirements=Requirements(
                    explicit=requirement_result.explicit_requirements,
                    implicit=requirement_result.implicit_requirements,
                ),
                selected_combo=selected_product_combo,
                # If risk is elevated, soften tone. We'll still talk, but more carefully.
                tone_policy="consultative"
                if orchestrator_result.risk_level in {"medium", "high"}
                else "professional_warm",
                short_memory=short_memory_dicts,
            )
            sales_result = await self.sales_agent.run(sales_input)

            # (debug) optionally expose the prompt sent to SalesAgent
            if os.getenv("TRACE_LLM_PROMPTS", "false").strip().lower() in {"1", "true", "yes", "y", "on"}:
                prompt_preview = (sales_input.debug_prompt or "").strip()
                if prompt_preview:
                    # Avoid flooding UI: keep a capped preview
                    phase_trace.append("--- SalesAgent prompt (preview) ---")
                    phase_trace.append(prompt_preview[:2000])

            # Phase 3: Guardrail
            phase_trace.append("Phase 3: GuardrailAgent")
            guardrail_input = GuardrailInput(response_text=sales_result.response_text, product_data=None)
            guardrail_result = await self.guardrail_agent.run(guardrail_input)

            if guardrail_result.approved:
                final_response_text = guardrail_result.modified_text or sales_result.response_text
            else:
                # Safe fallback if rejected
                final_response_text = (
                    "Mình chưa thể trả lời chắc chắn nội dung này ngay lúc này. "
                    "Mình sẽ chuyển cho nhân viên hỗ trợ tiếp nhé."
                )

            # If escalation is requested, prepend a short handoff notice but keep the sales reply.
            if orchestrator_result.task == "human_handle":
                phase_trace.append("Phase 3: Escalation note (human_handle)")
                handoff_note = "(Mình đã ghi nhận để nhân viên hỗ trợ thêm)\n\n"
                final_response_text = f"{handoff_note}{final_response_text}"

        # Receive assistant response into memory (store the final response)
        phase_trace.append("Phase 3: receive_input (assistant)")
        await memory_manager.receive_input(
            role="assistant",
            content=final_response_text,
            tokens=0,
            intent=intent_result.intent_code,
        )

        # Debug: Print agent results to console
        print_agent_results(
            intent_result=intent_result,
            handoff_result=handoff_result,
            orchestration_result=orchestrator_result.model_dump(),
        )

    # Update handoff_reason to PostgreSQL if task is human_handle
        if orchestrator_result.task == "human_handle":
            try:
                # Get or create session
                session = get_or_create_session(
                    session_id=session_id,
                    user_id=user_id,
                )

                # Update handoff_reason and metadata
                update_session_handoff(
                    session_id=session_id,
                    handoff_reason=orchestrator_result.handoff_reason,
                    metadata={
                        "task": orchestrator_result.task,
                        "intent_code": orchestrator_result.intent_code,
                        "clean_intent_text": orchestrator_result.clean_intent_text,
                        "risk_level": orchestrator_result.risk_level,
                        "handoff_required": orchestrator_result.handoff_required,
                        "summary": {
                            "intent": intent_result.model_dump(),
                            "handoff_analysis": handoff_result.model_dump(),
                            "orchestration": orchestrator_result.model_dump(),
                        },
                    },
                )
            except Exception as e:
                # Log error but don't fail the workflow
                print(f"Warning: Failed to update session handoff_reason in database: {e}")

        return {
            "intent": intent_result.model_dump(),
            "handoff_analysis": handoff_result.model_dump(),
            "orchestration": orchestrator_result.model_dump(),
            "final_response_text": final_response_text,
            "phase_trace": phase_trace,
        }
