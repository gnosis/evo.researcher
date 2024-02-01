import dotenv
import json
import os
import typing as t

from evo_researcher.functions.evaluate_question import evaluate_question, EvalautedQuestion
from evo_researcher.functions.research import research as research_evo
from evo_researcher.autonolas.research import (
    make_prediction,
    research as research_autonolas,
)
from evo_researcher.benchmark.utils import Prediction


def _make_prediction(
    market_question: str, additional_information: str
) -> Prediction:
    prediction = make_prediction(
        prompt=market_question, additional_information=additional_information
    )
    return Prediction.parse_obj(prediction)


class AbstractBenchmarkedAgent:
    def __init__(self, agent_name: str, max_workers: t.Optional[int] = None):
        self.agent_name = agent_name
        self.max_workers = max_workers  # Limit the number of workers that can run this worker in parallel threads

    def evaluate(self, market_question: str) -> EvalautedQuestion:
        raise NotImplementedError

    def research(self, market_question: str) -> t.Optional[str]:
        raise NotImplementedError
    
    def predict(self, market_question: str, researched: str) -> t.Optional[Prediction]:
        raise NotImplementedError

    def evaluate_research_predict(self, market_question: str) -> t.Optional[Prediction]:
        eval = self.evaluate(market_question=market_question)
        if not eval.is_predictable.answer:
            return None
        researched = self.research(market_question=market_question)
        return self.predict(
            market_question=market_question, 
            researched=researched
        ) if researched is not None else None


class OlasAgent(AbstractBenchmarkedAgent):
    def __init__(self, model: str, temperature: float, agent_name: str = "olas", max_workers: t.Optional[int] = None):
        super().__init__(agent_name=agent_name, max_workers=max_workers)
        self.model = model
        self.temperature = temperature
    def evaluate(self, market_question: str) -> EvalautedQuestion:
        return evaluate_question(question=market_question)

    def research(self, market_question: str) -> t.Optional[str]:
        try:
            return research_autonolas(
                prompt=market_question,
                engine=self.model,
            )
        except ValueError as e:
            print(f"Error in OlasAgent's research: {e}")
            return None
        
    def predict(self, market_question: str, researched: str) -> t.Optional[Prediction]:
        try:
            return _make_prediction(
                market_question=market_question,
                additional_information=researched,
                engine=self.model,
                temperature=self.temperature,
            )
        except ValueError as e:
            print(f"Error in OlasAgent's predict: {e}")
            return None

class EvoAgent(AbstractBenchmarkedAgent):
    def __init__(self, model: str, temperature: float, agent_name: str = "evo", max_workers: t.Optional[int] = None):
        super().__init__(agent_name=agent_name, max_workers=max_workers)
        self.model = model
        self.temperature = temperature

    def evaluate(self, market_question: str) -> EvalautedQuestion:
        return evaluate_question(question=market_question)

    def research(self, market_question: str) -> t.Optional[str]:
        dotenv.load_dotenv()
        open_ai_key = os.getenv("OPENAI_API_KEY")
        tavily_key = os.getenv("TAVILY_API_KEY")
        try:
            report, _ = research_evo(
                goal=market_question,
                openai_key=open_ai_key,
                tavily_key=tavily_key,
                model=self.model,
            )
            return report
        except ValueError as e:
            print(f"Error in EvoAgent's research: {e}")
            return None

    def predict(self, market_question: str, researched: str) -> t.Optional[Prediction]:
        try:
            return _make_prediction(
                market_question=market_question, 
                additional_information=researched,
                engine=self.model,
                temperature=self.temperature,
            )
        except ValueError as e:
            print(f"Error in EvoAgent's predict: {e}")
            return None


AGENTS = [
    OlasAgent,
    EvoAgent,
]
