#!/usr/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2013 Piotr Kaleta and Counsyl 
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import gnupg
import os

GNUPG_KEY_TYPE = "RSA"
GNUPG_KEY_LENGTH = 2048


class Encryptor(object):

    def __init__(self):
        self.gpg = gnupg.GPG()
        self.gpg.encoding = "utf-8"
        if self.gpg.list_keys() == []:
            self.generate_keypair()

    def generate_keypair(self):
        """Generate the RSA keypair."""
        input_data = self.gpg.gen_key_input(key_type=GNUPG_KEY_TYPE,
                                            key_length=GNUPG_KEY_LENGTH)
        key = self.gpg.gen_key(input_data)

        return key

    def export_keypair(self, key):
        public_key = self.gpg.export_keys(key)
        private_key = self.gpg.export_keys(key, True)

        return public_key, private_key

    def _get_fingerprint(self):
        """Return the fingerprint of the default key."""
        return self.gpg.list_keys()[0]["fingerprint"]

    def encrypt_file(self, input_file, output_filename):
        """Encrypt `input_file` (handle) and save results as `output_filename`."""
        fingerprint = self._get_fingerprint()

        self.gpg.encrypt_file(input_file, fingerprint,
                              output=output_filename)

    def encrypt(self, data):
        """Return the encrypted version of `data`."""
        return self.gpg.encrypt(data)

    def decrypt_file(self, input_filename, output_filename):
        """Decrypt `input_filename` and save results as `output_filename`."""
        with open(input_filename, "r") as input_file:
            self.gpg.decrypt_file(input_file, output=output_filename)

    def decrypt(self, data):
        """Return decrypted version of `data`."""
        return self.gpg.decrypt(data)
