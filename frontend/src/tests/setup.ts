import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })
// Os gráficos são mockados nos testes de página; QA visual real permanece separado.
