# Copyright Sierra

from typing import Optional, Union
from tau_bench.envs.base import Env
from tau_bench.envs.user import UserStrategy


def get_env(
    env_name: str,
    user_strategy: Union[str, UserStrategy],
    user_model: str,
    task_split: str,
    user_provider: Optional[str] = None,
    task_index: Optional[int] = None,
) -> Env:
    if env_name == "medical":
        from tau_bench.envs.medical import QIMedicalDomainEnv

        return QIMedicalDomainEnv(
            user_strategy=user_strategy,
            user_model=user_model,
            task_split=task_split,
            user_provider=user_provider,
            task_index=task_index,
        )
    else:
        raise ValueError(f"Unknown environment: {env_name}")
