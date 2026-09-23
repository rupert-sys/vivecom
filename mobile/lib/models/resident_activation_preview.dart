// Lo que la app muestra en vivo mientras el residente escribe su condominio y número de casa, antes de llenar
// el resto del registro (nombre, teléfono, contraseña) — ver GET /residents/activar/preview.
class ResidentActivationPreview {
  final String email;
  final String identificador;

  const ResidentActivationPreview({required this.email, required this.identificador});

  factory ResidentActivationPreview.fromJson(Map<String, dynamic> json) {
    return ResidentActivationPreview(
      email: json['email'] as String,
      identificador: json['identificador'] as String,
    );
  }
}
