import Dashboard from './pages/Dashboard.svelte';
import Products from './pages/Products.svelte';
import POS from './pages/POS.svelte';
import Sales from './pages/Sales.svelte';
import Insights from './pages/Insights.svelte';
import Expenses from './pages/Expenses.svelte';
import Alerts from './pages/Alerts.svelte';
import Sessions from './pages/Sessions.svelte';
export const routes = {
  '/': Dashboard,
  '/dashboard': Dashboard,
  '/products': Products,
  '/pos': POS,
  '/sales': Sales,
  '/insights': Insights,
  '/expenses': Expenses,
  '/alerts': Alerts,
  '/sessions': Sessions,
};