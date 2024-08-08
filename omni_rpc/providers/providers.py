import json
import os
import re

import requests

from omni_rpc.custom_logging import logger

PATH_TO_CHAINS = f"{os.getcwd()}/omni_rpc/chains/_data/chains"
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
        filename = f"{namespace}-{chain_id}.json"
        if os.path.exists(f"{PATH_TO_CHAINS}/{filename}"):
            return True
    return False


def get_chain_providers(chain_id: int) -> list:
    """
    Get the providers for the given chain_id.

    Args:
        chain_id (int): The chain_id for which the providers are to be fetched.

    Returns:
        dict: The providers for the given chain_id.
    """
    namespace = SUPPORTED_CAIP_2_NAMESPACES[0]
    filename = f"{namespace}-{chain_id}.json"
    with open(f"{PATH_TO_CHAINS}/{filename}", "r") as f:
        chain_data = json.load(f)
    providers = __filter_providers(chain_data["rpc"])
    return providers


def __filter_providers(providers: list) -> list:
    """
    Filters the providers to remove the ones that require an api key.

    Args:
        providers (list): The list of providers.

    Returns:
        list: The filtered list of providers.
    """
    # We filter rpc providers which have a placeholder ${...} and start
    # with wss://
    return [
        provider
        for provider in providers
        if not re.search(r".*\$\{.*\}|wss:\/\/.*", provider)
    ]


def forward_request(message: dict, providers: list) -> dict:
    """
    Forwards the request to the providers and merges the response.

    Args:
        message (dict): The message to be forwarded.
        providers (list): The list of providers.

    Returns:
        dict: The merged response from the providers.

    Raises:
        HTTPError: If the status code is not 200.
    """
    number_of_providers = len(providers)
    # responses = {}
    for provider in providers:
        logger.debug(f"Forwarding request to {provider}")
        response = requests.post(provider, json=message)
        logger.debug(
            f"Received response from {provider} with status code"
            f" {response.status_code}"
        )
        if number_of_providers == 1 and response.status_code != 200:
            response.raise_for_status()
        if response.status_code != 200:
            continue

        # we check if there is an error in the response
        data = response.json()
        if "error" in data:
            continue

        data = json.dumps(data)
        return json.loads(data)
        # This part has been used for aggregating responses from all providers
        # We will put that back in a later point of time with a subset of
        # providers
    #     if data not in responses:
    #         responses[data] = 1
    #     else:
    #         responses[data] += 1

    # selected_response = max(responses, key=responses.__getitem__)
    return json.loads(data)
