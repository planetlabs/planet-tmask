CC = gcc

test_gsl_bessel: test_gsl_bessel.cpp
	$(CC) -o test_gsl_bessel test_gsl_bessel.cpp `gsl-config --cflags --libs`
	./test_gsl_bessel

clean:
	rm test_gsl_bessel.o test_gsl_bessel || true
