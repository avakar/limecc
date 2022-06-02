#include <stdexcept>
#include <string>

#include "calc.hpp"
#include <iostream>
#include <string>

int main()
{
	std::string line;
	while (std::getline(std::cin, line))
	{
		try
		{
			parser p;
			p.push_data(line.data(), line.data() + line.size());
			std::cout << p.finish() << "\n";
		}
		catch (...)
		{
			std::cerr << "error: Invalid syntax.\n";
		}
	}
}
