@Tags(['integration'])
library;

import 'dart:io';

import 'package:app_residente/services/auth_service.dart';
import 'package:app_residente/services/clabe_service.dart';
import 'package:app_residente/services/statement_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Prueba de integración REAL para F1-29 — a diferencia del resto de la
// suite (que usa MockClient de package:http/testing.dart para no depender
// de infraestructura), esta prueba llama al backend de verdad corriendo en
// localhost:8000 contra Postgres.app real. NO corre en un `flutter test`
// normal ni en CI: necesita el servidor levantado con el tenant sembrado
// por el guion de QA de F1-29 (ver SEED_NOTES['F1-29'] en la bitácora para
// los pasos exactos — provisionar tenant vía /signup, crear residente con
// property_id, generar cargo, simular 4 depósitos SPEI firmados cubriendo
// cobro exacto/pago anticipado/saldo a favor/rechazo). Se corre a mano y
// aparte (`flutter test test/integration/real_backend_test.dart`), mismo
// criterio que las pruebas de integración reales del backend contra
// Postgres.app (test_signup.py, etc.) que tampoco corren en la suite
// SQLite por defecto.
//
// Objetivo: probar "residente ve su cargo → paga → ve confirmación" usando
// el código REAL de la app (AuthService, StatementService, ClabeService —
// sin ningún mock), algo que ninguna otra prueba de este proyecto hace,
// porque el simulador de iOS sigue bloqueado (mismo hueco documentado en
// F1-24 a F1-28: Xcode no seleccionado a nivel de sistema en esta Mac).
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  // flutter_test intercepta dart:io HttpClient por defecto (para que
  // ninguna prueba dependa sin querer de la red) — esta prueba SÍ quiere
  // red real, así que se apaga ese bloqueo explícitamente.
  HttpOverrides.global = null;

  const email = 'residente2@qaflujof129.mx';
  const password = 'ResidenteQA123';

  test('la app residente ve, contra el backend real, el resultado completo del flujo de cobro de F1-29', () async {
    SharedPreferences.setMockInitialValues({});
    final authService = AuthService();

    await authService.login(email, password);
    final token = await authService.obtenerToken();
    expect(token, isNotNull);

    final usuario = TokenPayload.decode(token!);
    expect(usuario.rol, 'residente');
    expect(usuario.propertyId, isNotNull);

    final estado = await StatementService().obtenerEstadoDeCuenta(usuario.propertyId!, token);

    expect(estado.identificador, 'Casa QA-1');
    // $350 depositados de más (no múltiplo exacto de la cuota) → saldo a
    // favor, no un cargo a medias (payment_reconciliation_service.py).
    expect(estado.saldoAFavor, 350.0);
    expect(estado.deudaTotal, 0.0);
    // Septiembre (cobro exacto) + octubre (pago anticipado, F1-08:
    // depósito exacto sin deuda pendiente crea el siguiente cargo ya
    // pagado) — ambos deben verse "pagado" desde la app residente.
    expect(estado.cargos, hasLength(2));
    expect(estado.cargos.every((c) => c.estado == 'pagado'), isTrue);
    expect(estado.pagos.where((p) => p.estado == 'confirmado'), hasLength(3));

    final clabe = await ClabeService().obtenerClabe(token);
    expect(clabe.clabeDestino, '999999999999999991');
  });
}
