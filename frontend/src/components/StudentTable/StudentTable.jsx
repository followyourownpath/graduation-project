import S from './styles.module.css';

export default function StudentTable({ students, onEdit, onDelete }) {
  if (!students.length) {
    return <p className={S.emptyState}>No students yet. Add one above.</p>
  }

  return (
    <div className={S.tableWrap}>
      <table className={S.studentTable}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Course</th>
            <th>Mark</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {students.map((s) => (
            <tr key={s.id}>
              <td>{s.name}</td>
              <td><code className={S.courseCode}>{s.course}</code></td>
              <td>
                <span className={`${S.markBadge} ${S[gradeClass(s.mark)]}`}>
                  {s.mark}
                </span>
              </td>
              <td>
                <div className={S.rowActions}>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => onEdit(s)}
                    aria-label={`Edit ${s.name}`}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm btn-danger"
                    onClick={() => onDelete(s.id)}
                    aria-label={`Delete ${s.name}`}
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const gradeClass = (mark) => {
  if (mark >= 85) return 'HD'
  if (mark >= 75) return 'D'
  if (mark >= 65) return 'C'
  if (mark >= 50) return 'P'
  return 'F'
}
