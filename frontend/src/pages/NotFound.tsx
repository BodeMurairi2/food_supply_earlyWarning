import { Link } from 'react-router-dom'
import { PageHeader } from '../components/ui'

export default function NotFound() {
  return (
    <>
      <PageHeader title="Page not found" />
      <Link to="/" className="btn-primary">Back to overview</Link>
    </>
  )
}
