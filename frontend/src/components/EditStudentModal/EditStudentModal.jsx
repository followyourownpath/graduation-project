import { useState, useEffect } from 'react'
import S from './styles.module.css'

export default function EditStudentModal({ student, onSave, onClose }) {
  const [name, setName] = useState(student.name)
  const [course, setCourse] = useState(student.course)
  const [mark, setMark] = useState(String(student.mark))

  useEffect(() => {
    setName(student.name)
    setCourse(student.course)
    setMark(String(student.mark))
  }, [student])

  const handleSubmit = (e) => {
    e.preventDefault()
    const m = Math.min(100, Math.max(0, Number(mark) || 0))
    onSave(student.id, { name: name.trim(), course: course.trim(), mark: m })
  }

  return (
    <div className={S.modalBackdrop} onClick={onClose}>
      <div className={S.modal} onClick={(e) => e.stopPropagation()}>
        <div className={S.modalHeader}>
          <h2>Edit student</h2>
          <button type="button" className="btn btn-icon" onClick={onClose} aria-label="Close">
            x
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className={S.formRow}>
            <label htmlFor="edit-name">Name</label>
            <input
              id="edit-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className={S.formRow}>
            <label htmlFor="edit-course">Course</label>
            <input
              id="edit-course"
              type="text"
              value={course}
              onChange={(e) => setCourse(e.target.value)}
              required
            />
          </div>
          <div className={S.formRow}>
            <label htmlFor="edit-mark">Mark (0–100)</label>
            <input
              id="edit-mark"
              type="number"
              min="0"
              max="100"
              value={mark}
              onChange={(e) => setMark(e.target.value)}
            />
          </div>
          <div className={S.modalActions}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
