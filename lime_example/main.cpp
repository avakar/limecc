#include "calc.hpp"
#include <iostream>
#include <string>

int main()
{
	std::string line;
	while (std::getline(std::cin, line))
	{
		lexer l;
		parser p;

		l.push_data(line.data(), line.data() + line.size(), p);
		l.finish(p);
		try
		{
			std::cout << p.finish() << "\n";
		}
		catch (...)
		{
			std::cerr << "error: Invalid syntax.\n";
		}
	}
}
