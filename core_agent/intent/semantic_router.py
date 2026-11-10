import numpy as np
from sentence_transformers import SentenceTransformer

from core_agent.intent.intent_detector import IntentDetector
from core_agent.models.task_understanding import TaskUnderstanding


class SemanticRouter(IntentDetector):
    """
    Embedding-based semantic intent router.
    Uses multiple utterances per route (description + all trigger phrases).
    At runtime: picks the route whose BEST utterance is closest to the query.
    """

    def __init__(
        self,
        encoder: SentenceTransformer,
        workflow_descriptions: dict[str, str],     # {workflow_id: description}
        workflow_primary_intents: dict[str, str],  # {workflow_id: primary_intent}
        workflow_trigger_phrases: dict[str, list[str]],  # {workflow_id: [phrases]}
        threshold: float = 0.40,
    ):
        self.encoder = encoder
        self.threshold = threshold
        self.workflow_primary_intents = workflow_primary_intents

        # Build multi-utterance index: {workflow_id: [vector, vector, ...]}
        # Each workflow is represented by its description + all trigger phrases.
        # At match time we take the MAX score across all utterances — whichever
        # example phrase is closest to the query determines the route.
        self.route_index: dict[str, list[np.ndarray]] = {}

        for wf_id, description in workflow_descriptions.items():
            triggers = workflow_trigger_phrases.get(wf_id, [])
            # All utterances for this route: description first, then trigger phrases
            utterances = [description] + triggers
            vectors = encoder.encode(utterances, normalize_embeddings=True)
            self.route_index[wf_id] = list(vectors)

    async def detect(self, message: str, history: str = "") -> TaskUnderstanding:
        # Route directly on the current user query to prevent past conversation
        # turns and long agent responses from overriding the current intent
        query_vec = self.encoder.encode([message], normalize_embeddings=True)[0]

        best_id, best_score = None, -1.0
        for wf_id, utterance_vecs in self.route_index.items():
            # Score = max similarity across all utterances for this route
            route_score = max(float(np.dot(query_vec, v)) for v in utterance_vecs)
            if route_score > best_score:
                best_score = route_score
                best_id = wf_id

        if best_id and best_score >= self.threshold:
            intent = self.workflow_primary_intents[best_id]
            confidence = round(best_score, 4)
        else:
            intent = "general_inquiry"
            confidence = round(best_score, 4) if best_score > 0 else 0.0

        return TaskUnderstanding(intent=intent, confidence=confidence, entities={})
