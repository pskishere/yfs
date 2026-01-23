import { StockModule } from '../domains/stock';
// import { ExampleModule } from '../domains/example';

export const initApp = () => {
  StockModule.init();
  // ExampleModule.init();
};
