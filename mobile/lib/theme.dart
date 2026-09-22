import 'package:flutter/material.dart';

/// Paleta formal de Vivecom — mismos tonos que el panel de administración (frontend/src/styles/tokens.css):
/// ledger / documento oficial de condominio, no un dashboard corporativo genérico ni una app de consumo.
class VivecomColors {
  static const ink = Color(0xFF1C2A39);
  static const ink2 = Color(0xFF16283A); // barra superior, chrome de énfasis
  static const inkSoft = Color(0xFF5C6773);
  static const paper = Color(0xFFF6F4EE);
  static const surface = Color(0xFFFFFFFF);
  static const surface2 = Color(0xFFFBFAF6);
  static const border = Color(0xFFD8D3C4);
  static const teal = Color(0xFF2F6F5E);
  static const tealStrong = Color(0xFF24594B);
  static const amber = Color(0xFF9A6B1F);
  static const brick = Color(0xFFA6432F);
  static const dustblue = Color(0xFF3E5C76);
}

final ThemeData temaVivecom = ThemeData(
  useMaterial3: true,
  scaffoldBackgroundColor: VivecomColors.paper,
  colorScheme: const ColorScheme.light(
    primary: VivecomColors.teal,
    onPrimary: Colors.white,
    secondary: VivecomColors.dustblue,
    onSecondary: Colors.white,
    error: VivecomColors.brick,
    onError: Colors.white,
    surface: VivecomColors.surface,
    onSurface: VivecomColors.ink,
    onSurfaceVariant: VivecomColors.inkSoft,
    outline: VivecomColors.border,
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: VivecomColors.ink2,
    foregroundColor: Colors.white,
    elevation: 0,
    centerTitle: false,
  ),
  cardTheme: CardThemeData(
    color: VivecomColors.surface,
    elevation: 0,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(10),
      side: const BorderSide(color: VivecomColors.border),
    ),
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      backgroundColor: VivecomColors.teal,
      foregroundColor: Colors.white,
      elevation: 0,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    ),
  ),
  outlinedButtonTheme: OutlinedButtonThemeData(
    style: OutlinedButton.styleFrom(
      foregroundColor: VivecomColors.teal,
      side: const BorderSide(color: VivecomColors.teal),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    ),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: VivecomColors.surface,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: VivecomColors.border),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: VivecomColors.border),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: VivecomColors.teal, width: 2),
    ),
  ),
  navigationBarTheme: NavigationBarThemeData(
    backgroundColor: VivecomColors.surface,
    indicatorColor: VivecomColors.teal.withValues(alpha: 0.14),
    labelTextStyle: WidgetStateProperty.resolveWith(
      (states) => TextStyle(
        fontSize: 11,
        fontWeight: states.contains(WidgetState.selected) ? FontWeight.w700 : FontWeight.w500,
        color: states.contains(WidgetState.selected) ? VivecomColors.tealStrong : VivecomColors.inkSoft,
      ),
    ),
    iconTheme: WidgetStateProperty.resolveWith(
      (states) => IconThemeData(
        color: states.contains(WidgetState.selected) ? VivecomColors.tealStrong : VivecomColors.inkSoft,
      ),
    ),
  ),
  cardColor: VivecomColors.surface,
  dividerColor: VivecomColors.border,
);
