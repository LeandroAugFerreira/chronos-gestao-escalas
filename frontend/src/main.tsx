import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from './app'
import { AuthProvider } from './hooks/auth'
import { ApiError } from './services/client'
import './styles/app.css'
import './styles/identity.css'

const cache = new QueryClient({ defaultOptions: { queries: { staleTime: 15000, retry: (count, error) => count < 1 && (!(error instanceof ApiError) || error.status === 0 || error.status >= 500) }, mutations: { retry: false } } })
createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={cache}><BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter></QueryClientProvider></React.StrictMode>)
