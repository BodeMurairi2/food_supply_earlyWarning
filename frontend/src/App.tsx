import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import AIAnalyst from './pages/AIAnalyst'
import { AppDataProvider } from './hooks/AppData'
import Forecasts from './pages/Forecasts'
import Historical from './pages/Historical'
import NotFound from './pages/NotFound'
import Overview from './pages/Overview'
import PredictionLab from './pages/PredictionLab'
import Visualizations from './pages/Visualizations'

export default function App() {
  return (
    <AppDataProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Overview />} />
            <Route path="historical" element={<Historical />} />
            <Route path="forecasts" element={<Forecasts />} />
            <Route path="prediction-lab" element={<PredictionLab />} />
            <Route path="visualizations" element={<Visualizations />} />
            <Route path="ai-analyst" element={<AIAnalyst />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppDataProvider>
  )
}
