# Protocol Coverage

Source of truth: `madVR Envy IP Control revision 1.1.3`.

## Commands

Implemented in `madvr_envy.commands` + `MadvrEnvyClient` wrappers:

- Connection: `Heartbeat`, `Bye`
- Power: `PowerOff`, `Standby`, `Restart`, `ReloadSoftware`
- Menu/GUI: `OpenMenu`, `CloseMenu`, `KeyPress`, `KeyHold`, `DisplayAlertWindow`, `CloseAlertWindow`, `DisplayMessage`, `DisplayAudioVolume`, `DisplayAudioMute`, `CloseAudioMute`
- Aspect ratio: `SetAspectRatioMode`
- Information: `GetIncomingSignalInfo`, `GetOutgoingSignalInfo`, `GetAspectRatio`, `GetMaskingRatio`, `GetTemperatures`, `GetMacAddress`
- Profiles: `CreateProfileGroup`, `RenameProfileGroup`, `DeleteProfileGroup`, `EnumProfileGroups`, `CreateProfile`, `RenameProfile`, `DeleteProfile`, `AddProfileToPage`, `RemoveProfileFromPage`, `ActivateProfile`, `GetActiveProfile`, `EnumProfiles`
- Options/pages: `EnumSettingPages`, `EnumConfigPages`, `EnumOptions`, `QueryOption`, `ChangeOption`
- System/demo: `Toggle`, `Hotplug`, `RefreshLicenseInfo`, `Force1080p60Output`

## Notifications

Parsed into typed messages in `madvr_envy.protocol`:

- Core: `WELCOME`, `OK`, `ERROR`
- Power/system: `PowerOff`, `Standby`, `Restart`, `ReloadSoftware`, `DisplayChanged`, `RefreshLicenseInfo`, `Force1080p60Output`, `Hotplug`, `FirmwareUpdate`, `MissingHeartbeat`
- Menu/GUI: `OpenMenu`, `CloseMenu`, `KeyPress`, `KeyHold`
- Signal/aspect: `NoSignal`, `IncomingSignalInfo`, `OutgoingSignalInfo`, `AspectRatio`, `MaskingRatio`, `SetAspectRatioMode`
- Profiles/pages: `CreateProfileGroup`, `RenameProfileGroup`, `DeleteProfileGroup`, `CreateProfile`, `RenameProfile`, `DeleteProfile`, `AddProfileToPage`, `RemoveProfileFromPage`, `ActivateProfile`, `ActiveProfile`, `ProfileGroup`, `ProfileGroup.`, `Profile`, `Profile.`, `SettingPage`, `SettingPage.`, `ConfigPage`, `ConfigPage.`
- Options: `Option`, `Option.`, `ChangeOption`, `InheritOption`, `ResetTemporary`
- 3DLUT: `Upload3DLUTFile`, `Rename3DLUTFile`, `Delete3DLUTFile`
- Settings management: `UploadSettingsFile`, `StoreSettings`, `RestoreSettings`
- Demo: `Toggle`, `ToneMapOn`, `ToneMapOff`

## Known Gaps

- Some command families from the full document are still pending typed wrappers/parsers for command-side operations (e.g. vendor-specific tooling flows related to file upload transport details).
- Enumeration transaction boundaries currently rely on end markers only; no request correlation IDs are modeled (spec does not define request IDs).
