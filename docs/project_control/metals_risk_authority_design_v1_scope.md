# Metals Risk Authority Design V1 Scope

This scope note accompanies the read-only risk-authority design audit.

The target restored family is `risk`, currently treated only as historical evidence. The new authority, if later approved, must be named `UIP_NATIVE_METALS_RISK_V1` and must remain `legacy_equivalent=false` unless a separate audit proves exact retired-methodology recovery.

The intended source boundary is the certified UIP-native Metals vehicle price-history authority (`UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1`, `UNADJUSTED_CLOSE`). No vehicle-derived risk metric may be silently re-labeled as commodity-level risk.

This phase authorizes only methodology design when evidence gates pass. It does not authorize a builder, production wiring, central publication staging, activation, or publisher re-enablement.
