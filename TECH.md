# Technical Details

## Vehicle Status JSON

### remainingChargingTimeToComplete_min

`charging > chargingStatus > value > remainingChargingTimeToComplete_min` is only available when `chargeMode` is set to `manual`. It is not available when `chargeMode` is set to `timer` which will be the case when your `preferredChargeMode` is set to `preferredChargingTimes`.
