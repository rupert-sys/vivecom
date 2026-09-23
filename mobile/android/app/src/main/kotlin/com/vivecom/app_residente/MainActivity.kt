package com.vivecom.app_residente

import io.flutter.embedding.android.FlutterFragmentActivity

// FlutterFragmentActivity (no FlutterActivity): el plugin local_auth (Face ID/huella para entrar más rápido,
// ver biometric_auth_service.dart) lo requiere en Android — usa un DialogFragment internamente para el
// prompt del sistema, que necesita una FragmentActivity de host.
class MainActivity : FlutterFragmentActivity()
