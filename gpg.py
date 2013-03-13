import gnupg
import os


GNUPG_DIRECTORY = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                               "gnupg")
GNUPG_KEY_TYPE = "RSA"
GNUPG_KEY_LENGTH = 2048


class Encryptor(object):

    def __init__(self):
        self.gpg = gnupg.GPG(gnupghome=GNUPG_DIRECTORY)
        self.gpg.encoding = "utf-8"
        if self.gpg.list_keys() == []:
            self.generate_keypair()

    def generate_keypair(self):
        input_data = self.gpg.gen_key_input(key_type=GNUPG_KEY_TYPE,
                                            key_length=GNUPG_KEY_LENGTH)
        key = self.gpg.gen_key(input_data)

        return key

    def export_keypair(self, key):
        public_key = self.gpg.export_keys(key)
        private_key = self.gpg.export_keys(key, True)

        return public_key, private_key

    def encrypt_file(self, input_filename, output_filename):
        fingerprint = self.gpg.list_keys()[0]["fingerprint"]

        with open(input_filename) as input_file:
            self.gpg.encrypt_file(input_file, fingerprint,
                                  output=output_filename)

    def decrypt(self, data):
        return self.gpg.decrypt(data)
