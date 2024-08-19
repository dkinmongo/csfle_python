import json
from flask import Flask, jsonify, request
from pymongo import MongoClient
from pymongo.encryption_options import AutoEncryptionOpts
from bson.json_util import dumps  # Import only dumps
from your_credentials import get_credentials

app = Flask(__name__)

# Retrieve credentials
credentials = get_credentials()
# MongoDB and Encryption Configuration
key_vault_db = "csfle"
key_vault_coll = "__keyVault"
key_vault_namespace = "csfle.__keyVault"

path = "./master-key.txt"
with open(path, "rb") as f:
    local_master_key = f.read()
kms_providers = {
    "local": {
        "key": local_master_key
    },
}
# end-kmsproviders

connection_string = credentials["MONGODB_URI"]
unencryptedClient = MongoClient(connection_string)
keyVaultClient = unencryptedClient[key_vault_db][key_vault_coll]

data_key_ids = {
    "dataKey1": keyVaultClient.find_one({"keyAltNames": "localKey1"})["_id"],
    "dataKey2": keyVaultClient.find_one({"keyAltNames": "localKey2"})["_id"],
    "dataKey3": keyVaultClient.find_one({"keyAltNames": "localKey3"})["_id"],
    "dataKey4": keyVaultClient.find_one({"keyAltNames": "localKey4"})["_id"],
}

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
                        "keyId": [data_key_ids["dataKey1"]],
                        "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Deterministic",
                    }
                },
                "billing": {
                    "encrypt": {
                        "bsonType": "object",
                        "keyId": [data_key_ids["dataKey2"]],
                        "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Random",
                    }
                }
            },
        },
        "medications": {
            "encrypt": {
                "bsonType": "array",
                "keyId": [data_key_ids["dataKey3"]],
                "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Random",
            }
        },
        "patientId": {
            "encrypt": {
                "bsonType": "int",
                "keyId": [data_key_ids["dataKey4"]],
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
                        "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Random",
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
                "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Random",
            }
        },
    },
}

patient_schema = {"localdb.patients": json_schema, "localdb.patients_pointer": json_schema_pointer}
extra_options = {"crypt_shared_lib_path": credentials["SHARED_LIB_PATH"]}

auto_encryption = AutoEncryptionOpts(
    kms_providers,
    key_vault_namespace,
    schema_map=patient_schema,
    **extra_options
)

secure_client = MongoClient(connection_string, auto_encryption_opts=auto_encryption)

encrypted_db_name="localdb"
encrypted_coll_name="patients"
#encrypted_coll_name="patients_pointer"

encrypted_coll = secure_client[encrypted_db_name][encrypted_coll_name]

# Existing Endpoints

@app.route('/patients', methods=['GET'])
def get_patients():
    first_name = request.args.get('firstName')
    if first_name:
        result = encrypted_coll.find_one({"firstName": first_name})
    else:
        result = list(encrypted_coll.find())

    print("Retrieved Document:", result)
    return json.dumps(result, default=str, ensure_ascii=False, indent=3)


@app.route('/patients/ssn/<ssn>', methods=['GET'])
def get_patient_by_ssn(ssn):
    result = encrypted_coll.find_one({"patientRecord.ssn": ssn})
    print("Retrieved Document:", result)
    return json.dumps(result, default=str, ensure_ascii=False, indent=3)

@app.route('/patients/<patient_id>', methods=['GET'])
def get_patient_by_id(patient_id):
    result = encrypted_coll.find_one({"patientId": int(patient_id)})
    print("Retrieved Document:", result)
    return json.dumps(result, default=str, ensure_ascii=False, indent=3)

@app.route('/patients/ssns', methods=['GET'])
def get_patients_by_ssns():
    ssns = request.args.getlist('ssns')
    results = list(encrypted_coll.find({"patientRecord.ssn": {"$in": ssns}}))
    print("Retrieved Document:", results)
    return json.dumps(results, default=str, ensure_ascii=False, indent=3)


@app.route('/patients/medications/<medication>', methods=['GET'])
def get_patient_by_medication(medication):
    result = encrypted_coll.find_one({"medications": medication})
    print("Retrieved Document:", result)
    return json.dumps(result, default=str, ensure_ascii=False, indent=3)


@app.route('/patients/billing', methods=['GET'])
def get_patient_by_billing():
    billing_info = request.json
    result = encrypted_coll.find_one({"patientRecord.billing": billing_info})
    print("Retrieved Document:", result)
    return json.dumps(result, default=str, ensure_ascii=False, indent=3)


# New Endpoint to Insert a Document
@app.route('/patients', methods=['POST'])
def add_patient():
    patient_data = request.json
    result = encrypted_coll.insert_one(patient_data)
    return jsonify({"status": "success", "inserted_id": str(result.inserted_id)}), 201

@app.route('/patients/<patient_id>', methods=['PUT'])
def update_patient(patient_id):
    update_data = request.json
    result = encrypted_coll.update_one(
        {"patientId": int(patient_id)},  # Use patientId as the filter
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        return jsonify({"status": "failure", "message": "Patient not found"}), 404
    else:
        return jsonify({"status": "success", "modified_count": result.modified_count}), 200

@app.route('/firstName/<firstname>', methods=['PUT'])
def update_firstname(firstname):
    update_data = request.json
    result = encrypted_coll.update_many(
        {"firstName": firstname},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        return jsonify({"status": "failure", "message": "Patient not found"}), 404
    else:
        return jsonify({"status": "success", "modified_count": result.modified_count}), 200

@app.route('/patients/<patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    result = encrypted_coll.delete_one({"patientId": int(patient_id)})

    if result.deleted_count == 0:
        return jsonify({"status": "failure", "message": "Patient not found"}), 404
    else:
        return jsonify({"status": "success", "message": "Patient deleted"}), 200


if __name__ == '__main__':
    app.run(debug=True)

