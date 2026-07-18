from apps.integrations.crypto import EncryptedTextField, decrypt, encrypt


def test_encrypt_decrypt_round_trip():
    original = "super-secret-token"

    ciphertext = encrypt(original)

    assert ciphertext != original
    assert decrypt(ciphertext) == original


def test_encrypted_text_field_get_prep_value_encrypts():
    field = EncryptedTextField()

    prepared = field.get_prep_value("plain-value")

    assert prepared != "plain-value"
    assert decrypt(prepared) == "plain-value"


def test_encrypted_text_field_from_db_value_decrypts():
    field = EncryptedTextField()
    stored = encrypt("plain-value")

    assert field.from_db_value(stored, None, None) == "plain-value"


def test_encrypted_text_field_handles_none_and_empty():
    field = EncryptedTextField()

    assert field.get_prep_value(None) is None
    assert field.from_db_value(None, None, None) is None
    assert field.get_prep_value("") == ""
    assert field.from_db_value("", None, None) == ""
