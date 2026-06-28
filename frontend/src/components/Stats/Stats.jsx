import { useState, useEffect } from 'react'
import { getStats } from '../../api';
import S from './styles.module.css'

export default function Stats() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getStats()
      .then((data) => {
        if (!cancelled) setStats(data)
      })
      .catch((e) => {
        if (!cancelled) setError(e.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  if (loading) return <p className={S.statsLoading}>Loading stats…</p>
  if (error) return <p className={S.statsError} role="alert">Stats: {error}</p>
  if (!stats) return null

  return (
    <section className={`${S.statsCard} card`}>
      <h2>Stats</h2>
      <dl className={S.statsGrid}>
        <div>
          <dt>Count</dt>
          <dd>{stats.count}</dd>
        </div>
        <div>
          <dt>Average</dt>
          <dd>{stats.average}</dd>
        </div>
        <div>
          <dt>Min</dt>
          <dd>{stats.min}</dd>
        </div>
        <div>
          <dt>Max</dt>
          <dd>{stats.max}</dd>
        </div>
      </dl>
    </section>
  )
}
