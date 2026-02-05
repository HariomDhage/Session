import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Manuals from './pages/Manuals'
import ManualDetail from './pages/ManualDetail'
import Sessions from './pages/Sessions'
import SessionDetail from './pages/SessionDetail'
import CreateManual from './pages/CreateManual'
import CreateSession from './pages/CreateSession'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="manuals" element={<Manuals />} />
          <Route path="manuals/create" element={<CreateManual />} />
          <Route path="manuals/:manualId" element={<ManualDetail />} />
          <Route path="sessions" element={<Sessions />} />
          <Route path="sessions/create" element={<CreateSession />} />
          <Route path="sessions/:sessionId" element={<SessionDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
