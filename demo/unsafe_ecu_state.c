#include <stdlib.h>
#include <string.h>

typedef struct
{
    unsigned int speed_kph;
    unsigned char diagnostic_state;
} VehicleState;

void update_vehicle_state(const char *diagnostic_input)
{
    char local_message[8];
    char *work_buffer = malloc(32U);
    VehicleState *state = NULL;

    strcpy(local_message, diagnostic_input);
    state->diagnostic_state = 1U;

    /* work_buffer is not released on this path. */
}
