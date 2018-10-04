import os

import maya
from constant_sorrow import constants
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurve
from cryptography.x509 import Certificate
from web3.middleware import geth_poa_middleware

from nucypher.blockchain.eth.agents import EthereumContractAgent, NucypherTokenAgent, MinerAgent
from nucypher.blockchain.eth.chains import Blockchain
from nucypher.config.constants import DEFAULT_CONFIG_ROOT
from nucypher.config.node import NodeConfiguration
from nucypher.crypto.powers import CryptoPower, SigningPower, EncryptingPower
from nucypher.utilities.sandbox.constants import TEST_URSULA_INSECURE_DEVELOPMENT_PASSWORD


class UrsulaConfiguration(NodeConfiguration):
    _name = 'ursula'
    DEFAULT_CONFIG_FILE_LOCATION = os.path.join(DEFAULT_CONFIG_ROOT, '{}.config'.format(_name))

    DEFAULT_REST_HOST = '127.0.0.1'
    DEFAULT_REST_PORT = 9151
    __DB_TEMPLATE = "ursula.{port}.db"
    DEFAULT_DB_NAME = __DB_TEMPLATE.format(port=DEFAULT_REST_PORT)

    __DEFAULT_TLS_CURVE = ec.SECP384R1

    def __init__(self,
                 rest_host: str = None,
                 rest_port: int = None,

                 # TLS
                 tls_curve: EllipticCurve = None,
                 tls_private_key: bytes = None,
                 certificate: Certificate = None,
                 certificate_filepath: str = None,

                 # Ursula
                 db_name: str = None,
                 db_filepath: str = None,
                 interface_signature=None,
                 crypto_power: CryptoPower = None,

                 # Blockchain
                 poa: bool = False,
                 provider_uri: str = None,
                 miner_agent: EthereumContractAgent = None,

                 *args, **kwargs
                 ) -> None:

        # REST
        self.rest_host = rest_host or self.DEFAULT_REST_HOST
        self.rest_port = rest_port or self. DEFAULT_REST_PORT
        self.db_name = db_name or self.__DB_TEMPLATE.format(port=self.rest_port)
        self.db_filepath = db_filepath or constants.UNINITIALIZED_CONFIGURATION

        #
        # TLS
        #
        self.tls_curve = tls_curve or self.__DEFAULT_TLS_CURVE
        self.tls_private_key = tls_private_key

        self.certificate = certificate
        self.certificate_filepath = certificate_filepath

        # Ursula
        self.interface_signature = interface_signature
        self.crypto_power = crypto_power

        #
        # Blockchain
        #
        self.poa = poa
        self.blockchain_uri = provider_uri
        self.miner_agent = miner_agent

        super().__init__(*args, **kwargs)

    def generate_runtime_filepaths(self, config_root: str) -> dict:
        base_filepaths = NodeConfiguration.generate_runtime_filepaths(config_root=config_root)
        filepaths = dict(db_filepath=os.path.join(config_root, self.db_name),
                         )
        base_filepaths.update(filepaths)
        return base_filepaths

    def write_defaults(self, tls: bool = True, *args, **kwargs):
        return super().write_defaults(tls=tls,
                                      host=self.rest_host,
                                      curve=self.tls_curve,
                                      *args, **kwargs)

    @property
    def static_payload(self) -> dict:
        payload = dict(
         rest_host=self.rest_host,
         rest_port=self.rest_port,
         db_name=self.db_name,
         db_filepath=self.db_filepath,
         certificate_filepath=self.certificate_filepath,
        )
        return {**super().static_payload, **payload}

    @property
    def dynamic_payload(self) -> dict:
        payload = dict(

            # Rest + TLS
            network_middleware=self.network_middleware,
            tls_curve=self.tls_curve,
            tls_private_key=self.tls_private_key,
            certificate=self.certificate,

            # Ursula
            interface_signature=self.interface_signature,
            timestamp=maya.now(),
            known_nodes=self.known_nodes,

            # Blockchain
            miner_agent=self.miner_agent
        )
        return {**super().dynamic_payload, **payload}

    def produce(self, **overrides):
        """Produce a new Ursula from configuration"""

        self.keyring.unlock(passphrase=TEST_URSULA_INSECURE_DEVELOPMENT_PASSWORD)  # TODO: where to get passphrase from?

        merged_parameters = {**self.static_payload, **self.dynamic_payload, **overrides}

        if self.federated_only is False:

            if not self.miner_agent:   # TODO: move this..?
                self.blockchain = Blockchain.connect(provider_uri=self.blockchain_uri, registry_filepath=self.registry_filepath)
                self.token_agent = NucypherTokenAgent(blockchain=self.blockchain)
                self.miner_agent = MinerAgent(token_agent=self.token_agent)
                merged_parameters.update(miner_agent=self.miner_agent)

            if self.poa:
                w3 = self.miner_agent.blockchain.interface.w3
                w3.middleware_stack.inject(geth_poa_middleware, layer=0)

        ursula = self._Character(**merged_parameters)

        # if self.save_metadata:
        ursula.write_node_metadata(node=ursula)
        ursula.save_certificate_to_disk(directory=ursula.known_certificates_dir)  # TODO: Move this..?

        if self.temp:
            class MockDatastoreThreadPool(object):
                def callInThread(self, f, *args, **kwargs):
                    return f(*args, **kwargs)
            ursula.datastore_threadpool = MockDatastoreThreadPool()

        return ursula


class AliceConfiguration(NodeConfiguration):
    from nucypher.characters.lawful import Alice

    _Character = Alice
    _name = 'alice'

    def __init__(self, policy_agent: EthereumContractAgent = None, *args, **kwargs) -> None:
        self.policy_agent = policy_agent
        super().__init__(*args, **kwargs)

    @property
    def static_payload(self) -> dict:
        alice_payload = dict(policy_agent=self.policy_agent)
        base_payload = super().static_payload
        alice_payload.update(base_payload)
        return base_payload


class BobConfiguration(NodeConfiguration):
    from nucypher.characters.lawful import Bob
    _Character = Bob
    _name = 'bob'
