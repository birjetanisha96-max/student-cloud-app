import unittest
import app as application

class StudentAppTests(unittest.TestCase):
    def setUp(self):
        application.students.clear()
        application.next_id = 1
        self.client = application.app.test_client()

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student Information System", response.data)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "healthy"})

    def test_add_and_list_student(self):
        response = self.client.post(
            "/students", json={"name": "Tanisha", "course": "BCA"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["id"], 1)
        listed = self.client.get("/students")
        self.assertEqual(len(listed.get_json()), 1)

    def test_validation(self):
        response = self.client.post("/students", json={"name": "", "course": "BCA"})
        self.assertEqual(response.status_code, 400)

    def test_delete_student(self):
        created = self.client.post(
            "/students", json={"name": "Asha", "course": "BCA"}
        )
        student_id = created.get_json()["id"]
        deleted = self.client.delete(f"/students/{student_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/students").get_json(), [])

if __name__ == "__main__":
    unittest.main()
