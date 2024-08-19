from pymongo import MongoClient
from pymongo.encryption_options import AutoEncryptionOpts
from pymongo.encryption import ClientEncryption
from bson import ObjectId
import pprint
from your_credentials import get_credentials

credentials = get_credentials()

# MongoDB configuration
key_vault_db = "csfle"
key_vault_coll = "__keyVault"
key_vault_namespace = "csfle.__keyVault"

provider = "aws"
kms_providers = {
    provider: {
        "accessKeyId": credentials["AWS_ACCESS_KEY_ID"],
        "secretAccessKey": credentials["AWS_SECRET_ACCESS_KEY"],
    }
}

connection_string = credentials["MONGODB_URI"]

# Connect to the unencrypted client to access the key vault
unencrypted_client = MongoClient(connection_string)
keyVaultClient = unencrypted_client[key_vault_db][key_vault_coll]

# Retrieve data key IDs
data_key_id_1 = keyVaultClient.find_one({"keyAltNames": "dataKey1"})["_id"]
data_key_id_2 = keyVaultClient.find_one({"keyAltNames": "dataKey2"})["_id"]
data_key_id_3 = keyVaultClient.find_one({"keyAltNames": "dataKey3"})["_id"]
data_key_id_4 = keyVaultClient.find_one({"keyAltNames": "dataKey4"})["_id"]

# start-schema
json_schema = {
    "bsonType": "object",
    "properties": {
        "patientRecord": {
            "bsonType": "object",
            "properties": {
                "ssn": {
                    "encrypt": {
                        "bsonType": "string",
                        "keyId": [data_key_id_1],
                        "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Deterministic",
                    }
                },
                "billing": {
                    "encrypt": {
                        "bsonType": "object",
                        "keyId": [data_key_id_2],
                        "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Random",
                    }
                }
            },
        },
        "medications": {
            "encrypt": {
                "bsonType": "array",
                "keyId": [data_key_id_3],
                "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Random",
            }
        },
        "patientId": {
            "encrypt": {
                "bsonType": "int",
                "keyId": [data_key_id_4],
                "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Deterministic",
            }
        },
    },
}

# Make All fields random to use json pointer to reference key-id
json_schema_pointer = {
    "bsonType": "object",
    "encryptMetadata": {"keyId": "/key-id"},
    "properties": {
        "patientRecord": {
            "bsonType": "object",
            "properties": {
                "ssn": {
                    "encrypt": {
                        "bsonType": "string",
                        "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Deterministic",
                    }
                },
                "billing": {
                    "encrypt": {
                        "bsonType": "object",
                        "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Random",
                    }
                }
            },
        },
        "medications": {
            "encrypt": {
                "bsonType": "array",
                "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Random",
            }
        },
        "patientId": {
            "encrypt": {
                "bsonType": "int",
                "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Deterministic",
            }
        },
    },
}

# Configure auto-encryption
patient_schema = {"db1.patients": json_schema, "db1.patients_pointer": json_schema_pointer}

extra_options = {"crypt_shared_lib_path": credentials["SHARED_LIB_PATH"]}

auto_encryption = AutoEncryptionOpts(
    kms_providers,
    key_vault_namespace,
    schema_map=patient_schema,
    **extra_options
)

encrypted_db_name="db1"
encrypted_coll_name="patients"

# Start the secure client
secure_client = MongoClient(connection_string, auto_encryption_opts=auto_encryption)
encrypted_coll = secure_client[encrypted_db_name][encrypted_coll_name]

# Read from non-encrypted collection
non_encrypted_coll = unencrypted_client["db1"]["patients_non_encrypted"]
patients_to_insert = []

# Fetch data from the non-encrypted collection
for patient in non_encrypted_coll.find():
    # Assuming the structure of the data matches the encrypted fields
    patients_to_insert.append(patient)

# Insert the patients into the encrypted collection
if patients_to_insert:
    result = encrypted_coll.insert_many(patients_to_insert)
    print(f"Inserted {len(result.inserted_ids)} documents into the encrypted collection.")
else:
    print("No patients found to insert.")

# Cleanup
unencrypted_client.close()
secure_client.close()

