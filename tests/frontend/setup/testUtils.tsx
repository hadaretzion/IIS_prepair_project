import { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, RenderOptions } from '@testing-library/react';

type RenderWithRouterOptions = RenderOptions & {
  route?: string;
};

export function renderWithRouter(ui: ReactElement, options: RenderWithRouterOptions = {}) {
  const { route = '/', ...renderOptions } = options;
  return render(<MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>, renderOptions);
}
