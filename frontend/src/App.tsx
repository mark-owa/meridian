import { Suspense, lazy } from 'react'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { PageSpinner } from './components/ui/Spinner'

const Dashboard = lazy(() => import('./pages/Dashboard').then((m) => ({ default: m.Dashboard })))
const KnowledgeBase = lazy(() =>
  import('./pages/KnowledgeBase').then((m) => ({ default: m.KnowledgeBase })),
)
const DocumentIntelligence = lazy(() =>
  import('./pages/DocumentIntelligence').then((m) => ({ default: m.DocumentIntelligence })),
)
const Leads = lazy(() => import('./pages/Leads').then((m) => ({ default: m.Leads })))

function withSuspense(element: React.ReactNode) {
  return <Suspense fallback={<PageSpinner />}>{element}</Suspense>
}

const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  { path: '/register', element: <Register /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <Layout />,
        children: [
          { path: '/', element: withSuspense(<Dashboard />) },
          { path: '/knowledge', element: withSuspense(<KnowledgeBase />) },
          { path: '/extraction', element: withSuspense(<DocumentIntelligence />) },
          { path: '/leads', element: withSuspense(<Leads />) },
        ],
      },
    ],
  },
])

export function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  )
}
