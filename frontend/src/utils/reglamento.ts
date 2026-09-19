// El recargo llega como fracción (0.05); se muestra como porcentaje entero o con
// decimales si los tiene (2.5%), sin ceros de sobra ni basura de coma flotante
// (0.07 * 100 = 7.000000000000001).
export function formatoPorcentaje(fraccion: number): string {
  return `${Number((fraccion * 100).toFixed(2))}%`
}
