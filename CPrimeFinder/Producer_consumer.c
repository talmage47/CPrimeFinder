//
//  Producer_consumer.c
//  A sample code to use mutex and pthread
//
//  Created by Ting Cao on 9/25/24.
//


#include <stdio.h>
#include <pthread.h>


#define MAX 10

// We need the mutex to make sure that every time only one thread access the buffer
// , could be the consumer thread or the producer thread.
pthread_mutex_t the_mutex;

// A blocked thread waits for the "traffic lights" before it make an action.
// The condition varibles are the "traffic lights" to tell the theads
// whether the job is done and resource, the buffer in this case, available
// or not. The following two condition varibles "condc" and "condp" are
// the traffic lights for consumer thread and producer thread.
pthread_cond_t condc, condp;

// To simplify the simulation, we use the integer varible as a buffer
// The buffer stores one uint of data, that is, a integer.
int buffer = 0;

void *producer(void *ptr)
{
    int i;
    for(i=1; i<=MAX; i++)
    {
    // Step 1, use the function to lock the mutex, therefore, only the
    // producer thread use the buffer after that. You do not want to enter
    // the "dressing room" when someone is using it. If the mutex has already
    // been locked, that means someone is using the "dressing room", the thread will
    // wait. Also, when you start to use the room, you need to lock the door so
    // other people knows someone is in the room.
        pthread_mutex_lock(&the_mutex);

    // Step 2, if the buffer is NOT empty, that means buffer hold some data
    // the thread need to wait for traffic light "condp" before output to the buffer,
        while(buffer !=0) pthread_cond_wait(&condp, &the_mutex);
    
    // Step 3, in this simulation, the producer generate one integer,
    // which is one unit of data assigned to the buffer.
        buffer = i*7;

    // Step 4, print out message tell what item the producer genetate.
        printf("producer produce item %d\n", buffer);
    
    // Step 5, since the buffer is only one unit, it is full now.
    // We need to stop, and notify the other thread, the consumer
    // thread that you are ready to go. So we use the following funtion
    // to change the traffic light for consumer thread to "green".
        pthread_cond_signal(&condc);
    
    // Step 6, after we give green light to the other thread,
    // we now unlock the mutex so the "dressing room" is available.
        pthread_mutex_unlock(&the_mutex);
    }

    // Step 7, exit the thread, return with 0, which means "success"
    pthread_exit(0);
    
}

void *consumer(void *ptr)
{
    
    int i;
    int get_data;
    for(i=1; i<=MAX; i++)
    {
        // Lock the_mutex before you start, see step 1 example in producer
        pthread_mutex_lock(&the_mutex);

        // When the buffer IS empty, nothing to consume, so we have to wait,
        // see step 2 example in producer

        while(buffer ==0) {
            pthread_cond_wait(&condc, &the_mutex);
        }

    // Assigned the buffer data to the varible get_data
    get_data = buffer;

        // Prints out the content of what you get in get_data
        printf("consumer consume item %d\n", get_data);

        // Clear the buffer by assigned value 0 to the buffer

        buffer = 0;

    // Notify the condition varible of producer that good to go
    // see step 5 example in producer
        pthread_cond_signal(&condp);

        // Unlock the mutex, see step 6 example in producer

        pthread_mutex_unlock(&the_mutex);
        // #6#END# DO NOT MODIFIE THIS COMMENT LINE!
    }
    
    // exit the thread, reurn with 0, which means "success", see step 7 in producer

    pthread_exit(0);

    
}

int main(int argc, char *argv[])
{



    pthread_t pro, con;
    pthread_mutex_init(&the_mutex, 0); // create the mutex used by thread
    pthread_cond_init(&condc,0);       // intialize the condition varible for consumer
    pthread_cond_init(&condp,0);       // initalize the condition varible for producer
    
    pthread_create(&con, 0, consumer, 0); // create thread map to function consumer
    pthread_create(&pro, 0, producer, 0); // create thread map to function producer
    pthread_join(pro,0);           // put the producer thread into the system
    pthread_join(con,0);          // put the consummer thread into the system

    // clean up, destroy the mutex and two threads
    pthread_cond_destroy(&condc);
    pthread_cond_destroy(&condp);
    pthread_mutex_destroy(&the_mutex);
    return 0;
}
