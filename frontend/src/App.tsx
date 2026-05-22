import { Toaster } from 'react-hot-toast'
import Dashboard from '@/pages/Dashboard'

export default function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#111d35',
            color: '#f1f5f9',
            border: '1px solid rgba(255,255,255,0.1)',
            fontFamily: 'DM Sans, sans-serif',
          },
          success: { iconTheme: { primary: '#4a6cf7', secondary: '#fff' } },
        }}
      />
      <Dashboard />
    </>
  )
}
