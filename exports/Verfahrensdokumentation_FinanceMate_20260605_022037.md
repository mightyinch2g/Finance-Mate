# Verfahrensdokumentation Finance Mate

Version: 0.6.44-top-tier-sme-erp-suite
Erstellt: 05.06.2026 02:20:37

## Systemzweck
Lokale Buchhaltungslösung für Kleinunternehmen mit Belegerfassung, Debitoren/Kreditoren, Zahlungen, Buchungsjournal, Berichten, Audit, GoBD-Export und Zahlungsverkehrsformaten.

## Datenhaltung
SQLite-Datenbank, lokale Anhänge, Import- und Exportordner. Tabellenexport im GoBD-Paket als JSON; DATEV-Export als CSV.

## Ordnungsmäßigkeitsfunktionen
- Festschreibung über posting_locks und festgeschrieben-Felder.
- Storno statt Löschen über reversal_entries und Stornojournal.
- Hash-Audit über gobd_hash_chain.
- Rollen/Benutzer über fm_users/fm_roles/fm_user_roles.
- Periodensperren über fiscal_periods.

## Schnittstellen
DATEV-Buchungsstapel CSV, GoBD-Prüferexport ZIP, ISO20022-nahe pain/camt/pain.002-Funktionen.

## Backup/Restore
ZIP-Sicherung für Datenbank, Anhänge, Importe und Exporte über _fm_backup_v641 und _fm_restore_v641.
