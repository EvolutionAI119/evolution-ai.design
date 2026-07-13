from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
from app.utils.logger import logger


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep(ABC):
    def __init__(self, name: str, step_type: str):
        self.name = name
        self.step_type = step_type
        self.status = StepStatus.PENDING
        self.progress = 0.0
        self.input_params: Dict[str, Any] = {}
        self.output_data: Dict[str, Any] = {}
        self.error_message: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def start(self):
        self.status = StepStatus.RUNNING
        self.started_at = datetime.now()
        logger.info(f"Starting step: {self.name}")

    def complete(self, output_data: Dict[str, Any]):
        self.status = StepStatus.COMPLETED
        self.output_data = output_data
        self.completed_at = datetime.now()
        self.progress = 100.0
        logger.info(f"Completed step: {self.name}")

    def fail(self, error_message: str):
        self.status = StepStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()
        logger.error(f"Failed step: {self.name} - {error_message}")


class Workflow(ABC):
    def __init__(self, name: str, workflow_type: str):
        self.name = name
        self.workflow_type = workflow_type
        self.status = WorkflowStatus.PENDING
        self.steps: List[WorkflowStep] = []
        self.current_step_index = 0
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    @abstractmethod
    def build_steps(self) -> List[WorkflowStep]:
        pass

    def initialize(self):
        self.steps = self.build_steps()
        logger.info(f"Workflow '{self.name}' initialized with {len(self.steps)} steps")

    def start(self):
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.now()
        logger.info(f"Starting workflow: {self.name}")

    def execute_step(self, step_index: int) -> Dict[str, Any]:
        if step_index >= len(self.steps):
            raise IndexError("Step index out of range")

        step = self.steps[step_index]
        step.start()

        try:
            prev_output = {}
            if step_index > 0:
                prev_output = self.steps[step_index - 1].output_data

            input_data = {**prev_output, **step.input_params}
            output_data = step.execute(input_data)
            step.complete(output_data)

            self.current_step_index = step_index + 1
            return output_data

        except Exception as e:
            step.fail(str(e))
            self.status = WorkflowStatus.FAILED
            raise

    def run_all(self) -> Dict[str, Any]:
        self.start()
        final_output = {}

        for i, step in enumerate(self.steps):
            try:
                output = self.execute_step(i)
                final_output.update(output)
            except Exception as e:
                logger.error(f"Workflow failed at step {i}: {step.name} - {str(e)}")
                self.status = WorkflowStatus.FAILED
                return final_output

        self.status = WorkflowStatus.COMPLETED
        self.completed_at = datetime.now()
        logger.info(f"Workflow completed: {self.name}")
        return final_output

    def get_progress(self) -> float:
        if not self.steps:
            return 0.0

        completed_count = sum(1 for step in self.steps if step.status == StepStatus.COMPLETED)
        return (completed_count / len(self.steps)) * 100.0

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.workflow_type,
            "status": self.status.value,
            "progress": self.get_progress(),
            "current_step": self.current_step_index,
            "total_steps": len(self.steps),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": [
                {
                    "name": step.name,
                    "type": step.step_type,
                    "status": step.status.value,
                    "progress": step.progress,
                    "error": step.error_message
                }
                for step in self.steps
            ]
        }