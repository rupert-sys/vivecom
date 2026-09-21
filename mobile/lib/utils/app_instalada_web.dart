import 'dart:js_interop';
import 'dart:js_interop_unsafe';

/// ¿La app web se abrió desde el ícono de la pantalla de inicio (modo «standalone»)? En iOS lo dice
/// `navigator.standalone`; en el resto, el media query `(display-mode: standalone)`. Si algo falla, se asume que no.
bool appInstalada() {
  try {
    final navegador = globalContext.getProperty<JSObject?>('navigator'.toJS);
    final ios = navegador?.getProperty<JSAny?>('standalone'.toJS);
    if (ios != null && ios.isA<JSBoolean>() && (ios as JSBoolean).toDart) return true;
    final consulta = globalContext.callMethod<JSObject?>('matchMedia'.toJS, '(display-mode: standalone)'.toJS);
    final coincide = consulta?.getProperty<JSAny?>('matches'.toJS);
    return coincide != null && coincide.isA<JSBoolean>() && (coincide as JSBoolean).toDart;
  } catch (_) {
    return false;
  }
}
