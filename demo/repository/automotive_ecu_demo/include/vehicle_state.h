#ifndef VEHICLE_STATE_H
#define VEHICLE_STATE_H

#include <stdint.h>

typedef struct
{
    uint8_t diagnostic_state;
    uint8_t operating_mode;
} VehicleState;

void update_vehicle_state(VehicleState *state, const char *diagnostic_input);

#endif
