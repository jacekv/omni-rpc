import os

SUPPORTED_CAIP_2_NAMESPACES = ["eip155"]


def check_provider_availability(chain_id: int) -> bool:
    """
    Checks if for the given chain_id, the provider is available or not.

    Args:
        chain_id (int): The chain_id for which the provider is to be checked.

    Returns:
        bool: True if provider is available, False otherwise.
    """
    for namespace in SUPPORTED_CAIP_2_NAMESPACES:
        if os.path.exists(
            f"{os.getcwd()}/omni_rpc/chains/_data/chains/{namespace}-{chain_id}.json"
        ):
            return True
    return False
