import unittest
import uuid
from app.discovery import validate_payload

class TestValidatePayload(unittest.TestCase):
    def test_valid_packet(self):
        uid = uuid.uuid4()
        payload = {
            "client_id": str(uid),
            "hostname": "host1",
            "installed_version": "1.0.0",
        }
        try:
            validate_payload(payload)
        except Exception as e:
            self.fail(f"validate_payload raised {e}")

    def test_missing_client_id(self):
        payload = {"hostname": "h", "installed_version": None}
        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_invalid_uuid(self):
        payload = {"client_id": "not-a-uuid", "hostname": "h", "installed_version": None}
        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_uuid_v1_rejected(self):
        payload = {"client_id": str(uuid.uuid1()), "hostname": "h", "installed_version": None}
        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_extra_keys(self):
        uid = uuid.uuid4()
        payload = {"client_id": str(uid), "hostname": "h", "installed_version": None, "extra": 1}
        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_missing_required_key(self):
        uid = uuid.uuid4()
        payload = {"client_id": str(uid), "hostname": "h"}
        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_nonstring_hostname(self):
        uid = uuid.uuid4()
        payload = {"client_id": str(uid), "hostname": 123, "installed_version": None}
        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_nonstring_installed_version(self):
        uid = uuid.uuid4()
        payload = {"client_id": str(uid), "hostname": None, "installed_version": 42}
        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_hostname_none_accepted(self):
        uid = uuid.uuid4()
        payload = {"client_id": str(uid), "hostname": None, "installed_version": "1.2"}
        validate_payload(payload)  # should not raise

    def test_installed_version_none_accepted(self):
        uid = uuid.uuid4()
        payload = {"client_id": str(uid), "hostname": "h", "installed_version": None}
        validate_payload(payload)

if __name__ == "__main__":
    unittest.main()
