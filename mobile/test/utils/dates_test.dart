import 'package:app_residente/utils/dates.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('utcNaiveToDateTime', () {
    test('interpreta un string naive del backend como UTC, no como hora local del dispositivo', () {
      // Comparar contra DateTime.utc(...) es independiente de la zona
      // horaria de la máquina donde corre la prueba (a diferencia de
      // comparar contra DateTime.now() o similar) — es la fuente de verdad
      // inequívoca de qué instante representa "2026-09-17T04:33:27" en UTC.
      final resultado = utcNaiveToDateTime('2026-09-17T04:33:27');
      final esperado = DateTime.utc(2026, 9, 17, 4, 33, 27);
      expect(resultado.isAtSameMomentAs(esperado), isTrue);

      // Si el bug real de F1-33 (mismo patrón, ver frontend/src/utils/dates.ts)
      // estuviera de vuelta aquí — parsear sin agregar 'Z' — Dart interpretaría
      // el string como hora LOCAL del dispositivo. Esto solo se puede probar
      // de forma determinista si la máquina que corre la prueba NO está en
      // UTC (Dart no permite forzar la zona horaria del proceso en caliente
      // como sí se pudo hacer con process.env.TZ en Node/Vitest).
      final offsetLocal = DateTime.now().timeZoneOffset;
      if (offsetLocal != Duration.zero) {
        final sinZInterpretadoComoLocal = DateTime.parse('2026-09-17T04:33:27');
        expect(sinZInterpretadoComoLocal.isAtSameMomentAs(esperado), isFalse);
      }
    });

    test('no duplica la Z si el string ya la trae', () {
      final resultado = utcNaiveToDateTime('2026-09-17T04:33:27Z');
      final esperado = DateTime.utc(2026, 9, 17, 4, 33, 27);
      expect(resultado.isAtSameMomentAs(esperado), isTrue);
    });
  });
}
