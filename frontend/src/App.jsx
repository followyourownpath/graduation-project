import { useState, useEffect } from 'react'
import { getStudents, createStudent, updateStudent, deleteStudent } from './api'
import StudentForm from './components/StudentForm'
import StudentTable from './components/StudentTable'
import EditStudentModal from './components/EditStudentModal'
import './App.css'
import Stats from './components/Stats'

export default function App() {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getStudents()
      setStudents(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleCreate = async (student) => {
    setError(null)
    try {
      const created = await createStudent(student)
      setStudents((prev) => [...prev, created])
    } catch (e) {
      setError(e.message)
    }
  }

  const handleUpdate = async (id, student) => {
    setError(null)
    try {
      const updated = await updateStudent(id, student)
      setStudents((prev) => prev.map((s) => (s.id === id ? updated : s)))
      setEditing(null)
    } catch (e) {
      setError(e.message)
    }
  }

  const handleDelete = async (id) => {
    setError(null)
    try {
      await deleteStudent(id)
      setStudents((prev) => prev.filter((s) => s.id !== id))
      if (editing?.id === id) setEditing(null)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Student Marks Manager</h1>
        <p className="tagline">Create and manage students and their marks</p>
      </header>

      <main className="main">
        <Stats />
        <section className="card form-card">
          <h2>Add a 3900 student</h2>
          <StudentForm onSubmit={handleCreate} />
        </section>

        {error && (
          <div className="banner banner-error" role="alert">
            {error}
          </div>
        )}

        <section className="card table-card">
          <h2>Students table</h2>
          {loading ? (
            <p className="loading">Loading…</p>
          ) : (
            <StudentTable
              students={students}
              onEdit={setEditing}
              onDelete={handleDelete}
            />
          )}
        </section>
      </main>

      {editing && (
        <EditStudentModal
          student={editing}
          onSave={handleUpdate}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  )
}
