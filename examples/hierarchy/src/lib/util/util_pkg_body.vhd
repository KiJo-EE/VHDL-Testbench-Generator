-- Package-Body bewusst in eigener Datei
library ieee;
use ieee.numeric_std.all;

package body util_pkg is
  function add9(a, b : std_logic_vector(7 downto 0)) return std_logic_vector is
  begin
    return std_logic_vector(('0' & unsigned(a)) + ('0' & unsigned(b)));
  end function;
end package body;
