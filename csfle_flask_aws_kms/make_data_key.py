from pymongo import MongoClient, ASCENDING
from pymongo.encryption_options import AutoEncryptionOpts
from pymongo.encryption import ClientEncryption
import base64
import os
from bson.codec_options import CodecOptions
from bson.binary import STANDARD, UUID
from your_credentials import get_credentials

credentials = get_credentials()


# start-kmsproviders
provider = "aws"
kms_providers = {
    provider: {
        "accessKeyId": credentials["AWS_ACCESS_KEY_ID"],
        "secretAccessKey": credentials["AWS_SECRET_ACCESS_KEY"],
    }
}
# end-kmsproviders

# start-datakeyopts
master_key = {
    "region": credentials["AWS_KEY_REGION"],
    "key": credentials["AWS_KEY_ARN"],
}
# end-datakeyopts

# start-create-index
connection_string = credentials["MONGODB_URI"]

key_vault_coll = "__keyVault"
key_vault_db = "csfle"
key_vault_namespace = f"{key_vault_db}.{key_vault_coll}"
key_vault_client = MongoClient(connection_string)
# Drop the Key Vault Collection in case you created this collection
# in a previous run of this application.
key_vault_client.drop_database(key_vault_db)
# Drop the database storing your encrypted fields as all
# the DEKs encrypting those fields were deleted in the preceding line.
key_vault_client["medicalRecords"].drop_collection("patients")
key_vault_client[key_vault_db][key_vault_coll].create_index(
    [("keyAltNames", ASCENDING)],
    unique=True,
    partialFilterExpression={"keyAltNames": {"$exists": True}},
)
# end-create-index


# start-create-dek
key_vault_database = "csfle"
key_vault_collection = "__keyVault"
key_vault_namespace = f"{key_vault_database}.{key_vault_collection}"

client = MongoClient(connection_string)
client_encryption = ClientEncryption(
    kms_providers,  # pass in the kms_providers variable from the previous step
    key_vault_namespace,
    client,
    CodecOptions(uuid_representation=STANDARD),
)

# Create data encryption keys and log messages
data_key_id_1 = client_encryption.create_data_key(
    provider, master_key=master_key, key_alt_names=["dataKey1"]
)
print(f"Key with ID {data_key_id_1} and keyAltName 'dataKey1' has been created.")

data_key_id_2 = client_encryption.create_data_key(
    provider, master_key=master_key, key_alt_names=["dataKey2"]
)
print(f"Key with ID {data_key_id_2} and keyAltName 'dataKey2' has been created.")

data_key_id_3 = client_encryption.create_data_key(
    provider, master_key=master_key, key_alt_names=["dataKey3"]
)
print(f"Key with ID {data_key_id_3} and keyAltName 'dataKey3' has been created.")

data_key_id_4 = client_encryption.create_data_key(
    provider, master_key=master_key, key_alt_names=["dataKey4"]
)
print(f"Key with ID {data_key_id_4} and keyAltName 'dataKey4' has been created.")

# end-create-dek
