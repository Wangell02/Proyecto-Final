#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>

using namespace std;

// Include definitions from DLDD-MAFF-JDLA.cpp to test parsearLote
// Let's create a minimal test runner that compiles with g++
int main() {
    ifstream f1("scratch/cvlac_ser.txt");
    stringstream b1;
    b1 << f1.rdbuf();
    string ser1 = b1.str();

    ifstream f2("scratch/gruplac_ser.txt");
    stringstream b2;
    b2 << f2.rdbuf();
    string ser2 = b2.str();

    cout << "Ser1 len: " << ser1.size() << endl;
    cout << "Ser2 len: " << ser2.size() << endl;
    return 0;
}
