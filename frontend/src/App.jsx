import { useState, useEffect } from 'react'

import testImg from './assets/test.jpeg'
import './App.css'

function App() {

  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function fetchHello() {
    setLoading(true)
    setMessage("Checking API...")
    try {
      const response = await fetch('/api/hello/')
      const data = await response.json()
      setMessage(data.message)
    } catch (error) {
      console.error('Error fetching hello message:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <h1>Git Gallery Scaffold</h1>
      <img src={testImg} alt="Test" />

      <div>
        <p>{message}</p>
        {loading && <p>Loading...</p>}
        <button onClick={fetchHello} disabled={loading}>Fetch Hello Message</button>
      </div>

    </>
  )
}

export default App
