#include <stdio.h>
#include <malloc.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define SPARSE_BITS 8
#define SPARSE_SIZE (1<<SPARSE_BITS)
#define SPARSE_MAXBITS (4 * SPARSE_BITS)

//this union can either contain copies of itself or just void pointers
union sparse_ptrarray {
  union sparse_ptrarray *sub[SPARSE_SIZE];
  void *ptr[SPARSE_SIZE];
};

int sparse_nodes = 0;
uint64_t bytes_used = 0;

void sparse_put(union sparse_ptrarray *arr, int idx, void *val) {
  union sparse_ptrarray *level = arr; //this seems to copy *arr to *level
  int bits_remaining;
  for(bits_remaining = SPARSE_MAXBITS; bits_remaining > SPARSE_BITS; bits_remaining -= SPARSE_BITS) { 
    //so we're doing this SPARSE_BITS at a time
    //shift idx by:
    //bits_remaining taken down an iteration, then flipping the last bit to 0
    //i think this 
    //& binds more tightly than >>
    int subidx = idx >> ((bits_remaining - SPARSE_BITS)) & (SPARSE_SIZE - 1);
    //if we can go down, go down and iterate again
    //in other words, this union contains itself
    if(level->sub[subidx]) level = level->sub[subidx]; 
    else {
      //the union contains an array of SPARSE_SIZE void pointers
      // a = b = c is equivalent to a = (b = c)
      // ...so this initializes the *sub array of new unions 
      level = level->sub[subidx] = calloc(sizeof(union sparse_ptrarray), 1);
      if(!level) {
	printf("calloc %d failed (%d nodes)\n", sizeof(union sparse_ptrarray), sparse_nodes);
	perror("calloc");
	exit(1);
      }
      //keep track of how large our uberarray is
      sparse_nodes++;
    }
  }
  //and then, in the lowest-down-level, put the thing
  level->ptr[idx & (SPARSE_SIZE - 1)] = val;
}

//same process as in PUT, but we know how deep it goes
void *sparse_get(union sparse_ptrarray *arr, int idx) {
  union sparse_ptrarray *level = arr;
  int bits_remaining;
  for(bits_remaining = SPARSE_MAXBITS; bits_remaining > SPARSE_BITS; bits_remaining -= SPARSE_BITS) {
    int subidx = idx >> ((bits_remaining - SPARSE_BITS)) & (SPARSE_SIZE - 1);
    if(level->sub[subidx]) level = level->sub[subidx];
    else return NULL;
  }
  return level->ptr[idx & (SPARSE_SIZE - 1)];
}

//sparse_get but tells us if there's something there
int sparse_exists(union sparse_ptrarray *arr, int idx) {
  union sparse_ptrarray *level = arr;
  int bits_remaining;
  for(bits_remaining = SPARSE_MAXBITS; bits_remaining > SPARSE_BITS; bits_remaining -= SPARSE_BITS) {
    int subidx = idx >> ((bits_remaining - SPARSE_BITS)) & (SPARSE_SIZE - 1);
    if(level->sub[subidx]) level = level->sub[subidx];
    else return 0;
  }
  return level->ptr[idx & (SPARSE_SIZE - 1)] != 0;
}

//basically recursively maps a function across the db with the same method
void sparse_map2(union sparse_ptrarray *arr, void (*fn)(void *), int bits_remaining) {
  if(bits_remaining > SPARSE_BITS) {
    int i;
    for(i = 0; i < SPARSE_SIZE; i++) {
      if(arr->sub[i]) sparse_map2(arr->sub[i], fn, bits_remaining - SPARSE_BITS);
    }
  } else { 
    int i;
    for(i = 0; i < SPARSE_SIZE; i++) {
      if(arr->ptr[i]) fn(arr->ptr[i]);
    }
 }
}

//...but dropped from orbit?
void sparse_map(union sparse_ptrarray *arr, void (*fn)(void *)) {
  sparse_map2(arr, fn, SPARSE_MAXBITS); 
}

void sparse_free2(union sparse_ptrarray *arr, int bits_remaining) {
  if(bits_remaining > SPARSE_BITS) {
    int i;
    for(i = 0; i < SPARSE_SIZE; i++) {
      if(arr->sub[i]) sparse_free2(arr->sub[i], bits_remaining - SPARSE_BITS);
    }
  }
  free(arr);
  bytes_used += sizeof(union sparse_ptrarray);
}

void sparse_free(union sparse_ptrarray *arr) {
  sparse_free2(arr, SPARSE_MAXBITS);
}

#define ENTRIES_PER_LINK 128

struct markov_entry {
  char *word;
  int nfollow;
  int maxfollow;
  char **follow;
  int *freq;
};

//
struct markov_bucket {
  int nents;
  int maxents;
  struct markov_entry **ents;
};

uint32_t hash(char *s) {	/* TODO: this could be optimized - use vector math etc */
  uint32_t h = 0;
  while(*s) {
    h = h * 31 + *(s++);
  }
  return h;
}

void markov_increment(union sparse_ptrarray *db, char *word, char *next) {
  int bucket_idx = hash(word);
  struct markov_bucket *bucket;
  if(sparse_exists(db, bucket_idx)) {
    bucket = (struct markov_bucket *) sparse_get(db, bucket_idx); //
  } else {
    bucket = calloc(sizeof(struct markov_bucket), 1); //calloc the bucket 
    bucket->ents = calloc(sizeof(struct markov_entry *), ENTRIES_PER_LINK);
    bucket->maxents = ENTRIES_PER_LINK;
    sparse_put(db, bucket_idx, bucket);
  }

  struct markov_entry *entry = 0;
  int i;
  for(i = 0; i < bucket->nents; i++) {
    if(!strcmp(bucket->ents[i]->word, word)) {
      entry = bucket->ents[i];
    }
  }
  if(!entry) {
    entry = calloc(sizeof(struct markov_entry), 1);
    bucket->nents++;
    if(bucket->nents > bucket->maxents) {
      bucket->maxents *= 2;
      bucket->ents = realloc(bucket->ents, sizeof(struct markov_entry *) * bucket->maxents);
    }
    bucket->ents[bucket->nents - 1] = entry;
    entry->word = strdup(word);
    entry->maxfollow = ENTRIES_PER_LINK;
    entry->follow = calloc(sizeof(char *), ENTRIES_PER_LINK);
    entry->freq = calloc(sizeof(int), ENTRIES_PER_LINK);
  }

  for(i = 0; i < entry->nfollow; i++) {
    if(!strcmp(entry->follow[i], next)) {
      entry->freq[i]++;
      return;
    }
  }

  entry->nfollow++;
  if(entry->nfollow > ENTRIES_PER_LINK) {
    entry->maxfollow *= 2;
    entry->follow = realloc(entry->follow, sizeof(char *) * entry->maxfollow);
    if(!entry->follow) {
      perror("realloc");
      exit(1);
    }
    entry->freq = realloc(entry->freq, sizeof(int) * entry->maxfollow);
    if(!entry->freq) {
      perror("realloc");
      exit(1);
    }
  }
  entry->follow[entry->nfollow - 1] = strdup(next);
  entry->freq[entry->nfollow - 1] = 1;
}

char *markov_predict(union sparse_ptrarray *db, char *word) {
  int bucket_idx = hash(word);
  struct markov_bucket *bucket;
  if(sparse_exists(db, bucket_idx)) {
    bucket = (struct markov_bucket *) sparse_get(db, bucket_idx);
  } else {
    return NULL;
  }

  struct markov_entry *entry = 0;
  int i;
  for(i = 0; i < bucket->nents; i++) {
    if(!strcmp(bucket->ents[i]->word, word)) {
      entry = bucket->ents[i];
    }
  }
  if(!entry) {
    return NULL;
  }

  int freq_max = 0;
  for(i = 0; i < entry->nfollow; i++) {
    freq_max += entry->freq[i];
  }
  if(freq_max == 0) return NULL;
  int n = rand() % freq_max;
  for(i = 0; i < entry->nfollow; i++) {
    n -= entry->freq[i];
    if(n < 0) return entry->follow[i];
  }
  return NULL;
}

void markov_free_bucket(struct markov_bucket *bucket) {
  int i, j;
  for(i = 0; i < bucket->nents; i++) {
    for(j = 0; j < bucket->ents[i]->nfollow; j++) {
      bytes_used += strlen(bucket->ents[i]->follow[j]) + 1;
      free(bucket->ents[i]->follow[j]);
    }
    bytes_used += strlen(bucket->ents[i]->word) + 1;
    bytes_used += sizeof(*bucket->ents[i]);
    bytes_used += (sizeof(int) + sizeof(char *)) * bucket->ents[i]->maxfollow;
    free(bucket->ents[i]->follow);
    free(bucket->ents[i]->freq);
    free(bucket->ents[i]->word);
    free(bucket->ents[i]);
  }
  bytes_used += sizeof(struct markov_entry *) * bucket->maxents;
  free(bucket->ents);
  bytes_used += sizeof(*bucket);
  free(bucket);
}

void markov_free_db(union sparse_ptrarray *arr) {
  bytes_used = 0;
  sparse_map(arr, (void (*)(void *)) markov_free_bucket);
  sparse_free(arr);
  printf("freed %d bytes\n", bytes_used);
}

void main() {
  srand(time(NULL));
  union sparse_ptrarray *arr = calloc(sizeof(union sparse_ptrarray), 1);
  struct timespec tstart={0,0}, tend={0,0};
  clock_gettime(CLOCK_MONOTONIC, &tstart);
  char message[2500];
  int n_pair = 0;
  int msgp = 0;
  while(1) {
    msgp = 0;
    while((message[msgp] = getchar()) != '\n') {
      if(message[msgp] == EOF) goto end;
      msgp++;
    }
    message[msgp] = 0;
    char *prev = strtok(message, " ");
    if(!prev) continue;
    //    printf("%d >%s\n", n_pair, prev);
    char *curr;
    while(curr = strtok(NULL, " ")) {
      markov_increment(arr, prev, curr);
      prev = curr;
      n_pair++;
    }
    markov_increment(arr, prev, "");
  }
 end:
  clock_gettime(CLOCK_MONOTONIC, &tend);
  printf("message processing took about %.5f seconds. %d pairs in that time means %.5f us/pair\n",
	 ((double)tend.tv_sec + 1.0e-9*tend.tv_nsec) - 
	 ((double)tstart.tv_sec + 1.0e-9*tstart.tv_nsec), n_pair, ((((double)tend.tv_sec + 1.0e-9*tend.tv_nsec) - 
								    ((double)tstart.tv_sec + 1.0e-9*tstart.tv_nsec))/n_pair)*1e6);
  printf("%d nodes allocated\n", sparse_nodes);
  markov_free_db(arr);
}
