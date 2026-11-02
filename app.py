from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# Demo-only in-memory storage. Data resets when the container restarts and
# is not shared between replicas. Use a database for persistent production data.
students = []
next_id = 1

PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Student Information System</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Arial, sans-serif; background: #f4f5fb; color: #20243a; }
    header { background: linear-gradient(120deg,#312e81,#6d28d9); color: white; padding: 32px 18px; text-align: center; }
    main { max-width: 850px; margin: 28px auto; padding: 0 16px; }
    .card { background: white; border-radius: 14px; padding: 22px; margin-bottom: 18px; box-shadow: 0 5px 22px #20243a12; }
    h1 { margin: 0 0 8px; } h2 { margin-top: 0; }
    form { display: grid; grid-template-columns: 1fr 1fr auto; gap: 10px; }
    input, button { font-size: 15px; padding: 12px; border-radius: 8px; }
    input { border: 1px solid #ccd0df; min-width: 0; }
    button { border: 0; background: #4f46e5; color: white; cursor: pointer; }
    button:hover { background: #3730a3; }
    button.delete { background: #dc2626; padding: 8px 12px; }
    .student { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:12px 0; border-bottom:1px solid #eee; }
    .student:last-child { border-bottom:0; }
    .muted { color:#69708a; } #message { min-height: 20px; color:#4338ca; }
    @media(max-width:620px) { form { grid-template-columns:1fr; } }
  </style>
</head>
<body>
<header>
  <h1>Student Information System</h1>
  <p>Cloud-native student record management</p>
</header>
<main>
  <section class="card">
    <h2>Add a student</h2>
    <form id="student-form">
      <input id="name" placeholder="Student name" required maxlength="80">
      <input id="course" placeholder="Course (e.g. BCA)" required maxlength="80">
      <button type="submit">Add student</button>
    </form>
    <p id="message" role="status"></p>
  </section>
  <section class="card">
    <h2>Student records</h2>
    <p class="muted">Use the button to refresh records. Demo records are stored in memory.</p>
    <button id="refresh" type="button">Refresh records</button>
    <div id="students" aria-live="polite"></div>
  </section>
</main>
<script>
async function loadStudents() {
  const response = await fetch('/students');
  const data = await response.json();
  const container = document.getElementById('students');
  container.replaceChildren();
  if (!data.length) {
    container.textContent = 'No students added yet.';
    return;
  }
  data.forEach(student => {
    const row = document.createElement('div');
    row.className = 'student';
    const label = document.createElement('span');
    label.textContent = `${student.name} — ${student.course} (ID: ${student.id})`;
    const button = document.createElement('button');
    button.className = 'delete';
    button.textContent = 'Delete';
    button.addEventListener('click', async () => {
      await fetch(`/students/${student.id}`, {method:'DELETE'});
      await loadStudents();
    });
    row.append(label, button);
    container.append(row);
  });
}
document.getElementById('student-form').addEventListener('submit', async event => {
  event.preventDefault();
  const message = document.getElementById('message');
  const response = await fetch('/students', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      name:document.getElementById('name').value,
      course:document.getElementById('course').value
    })
  });
  const result = await response.json();
  if (!response.ok) { message.textContent = result.error || 'Unable to add student'; return; }
  event.target.reset();
  message.textContent = 'Student added successfully.';
  await loadStudents();
});
document.getElementById('refresh').addEventListener('click', loadStudents);
loadStudents();
</script>
</body>
</html>
"""

@app.get("/")
def home():
    return render_template_string(PAGE)

@app.get("/health")
def health():
    return jsonify(status="healthy"), 200

@app.get("/students")
def get_students():
    return jsonify(students), 200

@app.post("/students")
def add_student():
    global next_id
    data = request.get_json(silent=True) or {}
    name = data.get("name", "")
    course = data.get("course", "")
    if not isinstance(name, str) or not isinstance(course, str):
        return jsonify(error="Name and course must be text"), 400
    name, course = name.strip(), course.strip()
    if not name or not course:
        return jsonify(error="Name and course are required"), 400
    if len(name) > 80 or len(course) > 80:
        return jsonify(error="Name and course must be 80 characters or fewer"), 400
    student = {"id": next_id, "name": name, "course": course}
    students.append(student)
    next_id += 1
    return jsonify(student), 201

@app.delete("/students/<int:student_id>")
def delete_student(student_id):
    for student in students:
        if student["id"] == student_id:
            students.remove(student)
            return jsonify(message="Student deleted"), 200
    return jsonify(error="Student not found"), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
