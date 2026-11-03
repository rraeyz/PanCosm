"""Flow manager: runs steps through the task queue and records each run in the project."""

from . import steps
from .tasks import TaskQueue


class Engine:
    def __init__(self, project=None, queue: TaskQueue | None = None):
        self.project = project
        self.queue = queue or TaskQueue()

    def run_step(self, step_id, inputs: dict, params: dict | None = None):
        params = params or {}
        steps.check_chain([step_id], inputs)
        run_id = self.project.start_run(step_id, inputs, params) if self.project else None
        task = self.queue.submit(steps.execute, step_id, inputs, params, name=step_id)
        if run_id is not None:

            def record(t):
                if t.finished:
                    self.project.finish_run(run_id, t.state, t._result if t.state == "done" else None, t.error)

            task.add_callback(record)
        return task

    def run_chain(self, step_ids, inputs: dict, params: dict | None = None) -> dict:
        """Run steps in order (blocking), feeding outputs forward. params: {step_id: {...}}."""
        params = params or {}
        steps.check_chain(step_ids, inputs)  # fail before running anything
        data = dict(inputs)
        for sid in step_ids:
            s = steps.get(sid)
            names = s.inputs + s.optional
            data.update(self.run_step(sid, {n: data[n] for n in names if n in data}, params.get(sid)).result())
        return data

    def shutdown(self):
        self.queue.shutdown()
