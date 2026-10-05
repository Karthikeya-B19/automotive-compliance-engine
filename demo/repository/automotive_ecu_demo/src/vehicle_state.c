#include "../include/vehicle_state.h"
#include <stdlib.h>
#include <string.h>

void update_vehicle_state(VehicleState *state, const char *diagnostic_input)
{
    char local_message[8];
    char *work_buffer = malloc(32U);
    VehicleState *target = NULL;

    strcpy(local_message, diagnostic_input);
    target->diagnostic_state = 1U;

    switch (state->operating_mode)
    {
        case 1U:
            state->diagnostic_state = 1U;
            break;
    }

    work_buffer[0] = '\0';
}
