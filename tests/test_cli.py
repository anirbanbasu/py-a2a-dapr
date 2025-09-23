# A practically useless test to test the useless hello world example.

import time
from uuid import uuid4
import pytest
from typer.testing import CliRunner
from py_a2a_dapr.client.a2a import cli_app as app
from py_a2a_dapr.model.task import EchoResponseWithHistory
import subprocess


class TestCLI:
    # TODO: Should this be a fixture instead?
    task_id = str(uuid4())

    @pytest.fixture(scope="class", autouse=True)
    def manage_dapr_sidecars(self):
        """
        Fixture to run Dapr sidecars before tests and clean up afterwards.
        """
        # The start script MUST fork out and return immediately.
        dapr_start_script = "./start_dapr_multi.sh"
        dapr_stop_script = "./stop_dapr_multi.sh"

        try:
            subprocess.run([dapr_start_script], shell=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Start script failed with error. {e}")
        except FileNotFoundError:
            pytest.fail(f"Start script not found at: {dapr_start_script}")

        # Wait for Dapr sidecars to be up and running
        time.sleep(8)
        # --- Yield control to tests ---
        yield

        # --- Teardown: Optional cleanup after tests ---
        # Stop Dapr sidecars
        try:
            subprocess.run([dapr_stop_script], shell=True, text=True)
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Stop script failed with error {e}")
        except FileNotFoundError:
            pytest.fail(f"Stop script not found at: {dapr_stop_script}")

    def test_hello(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["hello", "Tester"])
        assert result.exit_code == 0
        assert "Hello, Tester!" in result.stdout

    @pytest.mark.parametrize("iterations", range(5))
    def test_single_a2a_actor(self, manage_dapr_sidecars, iterations: int) -> None:
        # Iterations are there to create a history in the response.
        runner = CliRunner()
        message = f"Hello there! {iterations}"
        result = runner.invoke(
            app, ["single-a2a-actor", "--task-id", self.task_id, message]
        )
        assert result.exit_code == 0
        validated_response = EchoResponseWithHistory.model_validate_json(result.stdout)
        assert validated_response.current.input == message
        assert message in validated_response.current.output
        if iterations > 1:
            assert len(validated_response.past) >= (iterations - 1)
