import { useState } from 'react'
import S from './styles.module.css';

const emptyForm = { name: '', course: '', mark: '' }

export default function StudentForm({ onSubmit }) {
  const [form, setForm] = useState(emptyForm)

  function handleChange(e) {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    const name = form.name.trim()
    const course = form.course.trim()
    if (!name || !course) return
    const mark = form.mark === '' ? 0 : Math.min(100, Math.max(0, Number(form.mark) || 0))
    onSubmit({ name, course, mark })
    setForm(emptyForm)
  }

  return (
    <form className={S.studentForm} onSubmit={handleSubmit}>
      <div className={S.formRow}>
        <label htmlFor="name">Name</label>
        <input
          id="name"
          name="name"
          type="text"
          placeholder="e.g. Jane Doe"
          value={form.name}
          onChange={handleChange}
          required
        />
      </div>
      <div className={S.formRow}>
        <label htmlFor="course">Course</label>
        <input
          id="course"
          name="course"
          type="text"
          placeholder="e.g. COMP1531"
          value={form.course}
          onChange={handleChange}
          required
        />
      </div>
      <div className={S.formRow}>
        <label htmlFor="mark">Mark (0-100)</label>
        <input
          id="mark"
          name="mark"
          type="number"
          min="0"
          max="100"
          placeholder="0"
          value={form.mark}
          onChange={handleChange}
        />
      </div>
      <button type="submit" className="btn btn-primary">
        Add student
      </button>
    </form>
  )
}
